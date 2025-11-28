"""
Reconciliation module using Integer Linear Programming (ILP).

Uses PuLP to formulate an optimization problem that selects the best subset
of invoice line items while respecting constraints like reported totals and
duplicate groups.
"""

from typing import List, Dict, Optional, Set, Tuple

import pulp


def ilp_reconcile(
    candidates: List[Dict],
    reported_total: Optional[float] = None,
    duplicate_groups: Optional[List[List[int]]] = None,
    tolerance: float = 1.0
) -> Dict:
    """
    Select optimal subset of candidates using Integer Linear Programming.
    
    Formulates and solves an ILP to maximize total confidence while
    optionally matching a reported total and respecting duplicate constraints.
    
    Args:
        candidates: List of candidate dicts with 'id', 'amount', 'conf'
        reported_total: Target total amount to match (optional)
        duplicate_groups: List of ID groups where at most one should be selected
        tolerance: Allowed deviation from reported_total
    
    Returns:
        Dictionary containing:
            - 'selected_ids': List of selected candidate IDs
            - 'selected_total': Sum of selected amounts
            - 'deviation': Absolute deviation from reported_total (0 if no target)
            - 'status': 'ok' if solution found, 'infeasible' otherwise
    
    Algorithm:
        - Binary variable x_i for each candidate (1 = selected, 0 = not)
        - Maximize: sum(conf_i * x_i) - penalty * z
        - Where z = auxiliary variable for absolute deviation from target
        - Constraints:
          1. Sum of selected amounts within tolerance of reported_total
          2. At most one candidate per duplicate group
    
    Examples:
        >>> candidates = [
        ...     {'id': 1, 'amount': 100.0, 'conf': 90.0},
        ...     {'id': 2, 'amount': 200.0, 'conf': 85.0}
        ... ]
        >>> result = ilp_reconcile(candidates, reported_total=300.0)
        >>> result['status']
        'ok'
    """
    if not candidates:
        return {
            'selected_ids': [],
            'selected_total': 0.0,
            'deviation': 0.0,
            'status': 'ok'
        }
    
    # Filter out candidates with None amounts
    valid_candidates = [c for c in candidates if c.get('amount') is not None]
    if not valid_candidates:
        return {
            'selected_ids': [],
            'selected_total': 0.0,
            'deviation': 0.0 if reported_total is None else abs(reported_total),
            'status': 'no_valid_amounts'
        }
    
    # Use only valid candidates
    candidates = valid_candidates
    
    # Create the optimization problem
    prob = pulp.LpProblem("Invoice_Reconciliation", pulp.LpMaximize)
    
    # Create binary decision variables for each candidate
    x_vars = {}
    for candidate in candidates:
        cand_id = candidate['id']
        x_vars[cand_id] = pulp.LpVariable(f"x_{cand_id}", cat='Binary')
    
    # Objective function components
    objective_terms = []
    
    # Add confidence-based selection rewards
    for candidate in candidates:
        cand_id = candidate['id']
        conf = candidate.get('conf', 0.0)
        objective_terms.append(conf * x_vars[cand_id])
    
    # If reported_total provided, add deviation penalty
    z_var = None
    if reported_total is not None:
        # Create auxiliary variables for absolute deviation
        z_plus = pulp.LpVariable("z_plus", lowBound=0, cat='Continuous')
        z_minus = pulp.LpVariable("z_minus", lowBound=0, cat='Continuous')
        
        # z represents absolute deviation
        z_var = z_plus + z_minus
        
        # Penalize deviation heavily (penalty weight = 10)
        penalty = 10.0
        objective_terms.append(-penalty * z_var)
        
        # Constraint: selected_total - reported_total = z_plus - z_minus
        selected_total_expr = pulp.lpSum([
            candidate['amount'] * x_vars[candidate['id']]
            for candidate in candidates
        ])
        
        prob += (
            selected_total_expr - reported_total == z_plus - z_minus,
            "Total_Deviation"
        )
        
        # Constraint: deviation must be within tolerance
        prob += (z_var <= tolerance, "Tolerance_Constraint")
    
    # Set objective function
    prob += pulp.lpSum(objective_terms), "Objective"
    
    # Add duplicate group constraints
    if duplicate_groups:
        for group_idx, group_ids in enumerate(duplicate_groups):
            # At most one candidate from each group
            group_vars = [x_vars[cand_id] for cand_id in group_ids if cand_id in x_vars]
            if group_vars:
                prob += (
                    pulp.lpSum(group_vars) <= 1,
                    f"Duplicate_Group_{group_idx}"
                )
    
    # Solve the problem
    solver = pulp.PULP_CBC_CMD(msg=False)
    prob.solve(solver)
    
    # Extract results
    status = pulp.LpStatus[prob.status]
    
    if status != 'Optimal':
        return {
            'selected_ids': [],
            'selected_total': 0.0,
            'deviation': 0.0 if reported_total is None else abs(reported_total),
            'status': 'infeasible'
        }
    
    # Collect selected candidates
    selected_ids = []
    selected_total = 0.0
    
    for candidate in candidates:
        cand_id = candidate['id']
        if x_vars[cand_id].varValue and x_vars[cand_id].varValue > 0.5:
            selected_ids.append(cand_id)
            amount = candidate.get('amount', 0.0) or 0.0  # Handle None
            selected_total += amount
    
    # Calculate deviation
    deviation = 0.0
    if reported_total is not None:
        deviation = abs(selected_total - reported_total)
    
    return {
        'selected_ids': selected_ids,
        'selected_total': round(selected_total, 2),
        'deviation': round(deviation, 2),
        'status': 'ok'
    }


def make_duplicate_groups_from_candidates(candidates: List[Dict]) -> List[List[int]]:
    """
    Identify duplicate groups based on exact description and amount matches.
    
    Groups candidates that have identical (description, amount) pairs.
    These are likely duplicates where only one should be selected.
    
    Args:
        candidates: List of candidate dictionaries
    
    Returns:
        List of ID groups, where each group contains candidate IDs
        with identical (desc, amount) tuples
    
    Examples:
        >>> candidates = [
        ...     {'id': 1, 'desc': 'Item A', 'amount': 100.0},
        ...     {'id': 2, 'desc': 'Item A', 'amount': 100.0},
        ...     {'id': 3, 'desc': 'Item B', 'amount': 200.0}
        ... ]
        >>> make_duplicate_groups_from_candidates(candidates)
        [[1, 2]]
    """
    if not candidates:
        return []
    
    # Build a mapping from (desc, amount) -> list of IDs
    key_to_ids: Dict[Tuple[str, float], List[int]] = {}
    
    for candidate in candidates:
        desc = candidate.get('desc', '').strip().lower()
        amount = candidate.get('amount')
        
        # Skip candidates without amount
        if amount is None:
            continue
        
        # Round amount to avoid floating point precision issues
        amount_rounded = round(amount, 2)
        
        key = (desc, amount_rounded)
        
        if key not in key_to_ids:
            key_to_ids[key] = []
        
        key_to_ids[key].append(candidate['id'])
    
    # Extract groups with more than one candidate
    duplicate_groups = []
    
    for key, id_list in key_to_ids.items():
        if len(id_list) > 1:
            duplicate_groups.append(id_list)
    
    return duplicate_groups


def main():
    """
    Demonstrate ILP reconciliation with synthetic examples.
    """
    print("=" * 70)
    print("ILP RECONCILIATION DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Test Case 1: Simple selection without target
    print("Test Case 1: Select best candidates (no target total)")
    print("-" * 70)
    
    candidates_1 = [
        {'id': 1, 'desc': 'Item A', 'amount': 100.0, 'conf': 95.0},
        {'id': 2, 'desc': 'Item B', 'amount': 200.0, 'conf': 85.0},
        {'id': 3, 'desc': 'Item C', 'amount': 150.0, 'conf': 90.0},
        {'id': 4, 'desc': 'Item D', 'amount': 50.0, 'conf': 70.0},
    ]
    
    print("Candidates:")
    for c in candidates_1:
        print(f"  ID {c['id']}: {c['desc']:10s} ${c['amount']:6.2f} (conf: {c['conf']:4.1f})")
    print()
    
    result_1 = ilp_reconcile(candidates_1)
    
    print("Result:")
    print(f"  Status: {result_1['status']}")
    print(f"  Selected IDs: {result_1['selected_ids']}")
    print(f"  Selected Total: ${result_1['selected_total']:.2f}")
    print(f"  Deviation: ${result_1['deviation']:.2f}")
    print()
    
    # Test Case 2: Match a reported total
    print("=" * 70)
    print("Test Case 2: Match reported total of $450.00")
    print("-" * 70)
    
    candidates_2 = [
        {'id': 1, 'desc': 'Item A', 'amount': 100.0, 'conf': 95.0},
        {'id': 2, 'desc': 'Item B', 'amount': 200.0, 'conf': 85.0},
        {'id': 3, 'desc': 'Item C', 'amount': 150.0, 'conf': 90.0},
        {'id': 4, 'desc': 'Item D', 'amount': 50.0, 'conf': 70.0},
    ]
    
    reported_total = 450.0
    
    print("Candidates:")
    for c in candidates_2:
        print(f"  ID {c['id']}: {c['desc']:10s} ${c['amount']:6.2f} (conf: {c['conf']:4.1f})")
    print(f"\nReported Total: ${reported_total:.2f}")
    print()
    
    result_2 = ilp_reconcile(candidates_2, reported_total=reported_total, tolerance=1.0)
    
    print("Result:")
    print(f"  Status: {result_2['status']}")
    print(f"  Selected IDs: {result_2['selected_ids']}")
    print(f"  Selected Total: ${result_2['selected_total']:.2f}")
    print(f"  Deviation: ${result_2['deviation']:.2f}")
    
    # Verify which items were selected
    selected_items = [c for c in candidates_2 if c['id'] in result_2['selected_ids']]
    print(f"\n  Selected Items:")
    for c in selected_items:
        print(f"    - {c['desc']}: ${c['amount']:.2f}")
    print()
    
    # Test Case 3: With duplicate groups
    print("=" * 70)
    print("Test Case 3: Handle duplicates (Items 2 and 3 are duplicates)")
    print("-" * 70)
    
    candidates_3 = [
        {'id': 1, 'desc': 'Item A', 'amount': 100.0, 'conf': 95.0},
        {'id': 2, 'desc': 'Widget X', 'amount': 200.0, 'conf': 85.0},
        {'id': 3, 'desc': 'Widget X', 'amount': 200.0, 'conf': 92.0},  # Duplicate with higher conf
        {'id': 4, 'desc': 'Item D', 'amount': 50.0, 'conf': 70.0},
    ]
    
    print("Candidates:")
    for c in candidates_3:
        print(f"  ID {c['id']}: {c['desc']:10s} ${c['amount']:6.2f} (conf: {c['conf']:4.1f})")
    print()
    
    # Detect duplicate groups
    duplicate_groups = make_duplicate_groups_from_candidates(candidates_3)
    print(f"Detected duplicate groups: {duplicate_groups}")
    print()
    
    result_3 = ilp_reconcile(
        candidates_3,
        reported_total=350.0,
        duplicate_groups=duplicate_groups,
        tolerance=1.0
    )
    
    print("Result:")
    print(f"  Status: {result_3['status']}")
    print(f"  Selected IDs: {result_3['selected_ids']}")
    print(f"  Selected Total: ${result_3['selected_total']:.2f}")
    print(f"  Deviation: ${result_3['deviation']:.2f}")
    
    selected_items_3 = [c for c in candidates_3 if c['id'] in result_3['selected_ids']]
    print(f"\n  Selected Items:")
    for c in selected_items_3:
        print(f"    - ID {c['id']}: {c['desc']} (${c['amount']:.2f}, conf: {c['conf']:.1f})")
    print(f"\n  Note: ID 3 selected over ID 2 due to higher confidence (92.0 vs 85.0)")
    print()
    
    print("=" * 70)
    print("All tests complete!")


if __name__ == "__main__":
    main()
