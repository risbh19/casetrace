from collections import deque
from decimal import Decimal

from networkx import DiGraph


def build_graph(transactions) -> dict:
    accounts: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}
    outgoing: dict[str, set[str]] = {}
    incoming: set[str] = set()
    for tx in transactions:
        for account in (tx.from_acc, tx.to_acc):
            accounts.setdefault(account, {"id": account, "balance_remaining": None})
            outgoing.setdefault(account, set())
        outgoing[tx.from_acc].add(tx.to_acc)
        incoming.add(tx.to_acc)
        edge = edges.setdefault(
            (tx.from_acc, tx.to_acc),
            {"source": tx.from_acc, "target": tx.to_acc, "amount": Decimal(0), "transfers": 0},
        )
        edge["amount"] += tx.amount
        edge["transfers"] += 1
        if tx.balance_remaining is not None:
            accounts[tx.to_acc]["balance_remaining"] = tx.balance_remaining

    graph = DiGraph(list(edges))
    roots = [account for account in accounts if account not in incoming]
    levels: dict[str, int] = {}
    for root in roots + list(accounts):
        if root in levels:
            continue
        frontier = deque([(root, 0)])
        while frontier:
            account, tier = frontier.popleft()
            if account in levels:
                continue
            levels[account] = tier
            successors = graph.successors(account)
            frontier.extend((child, tier + 1) for child in sorted(successors) if child not in levels)

    priorities = []
    for account, entry in accounts.items():
        balance = entry["balance_remaining"]
        entry["tier"] = levels[account]
        entry["freeze_priority"] = not outgoing[account] and balance is not None and balance > 0
        entry["balance_remaining"] = str(balance) if balance is not None else None
        if entry["freeze_priority"]:
            priorities.append(entry)
    priorities.sort(key=lambda entry: Decimal(entry["balance_remaining"]), reverse=True)
    for edge in edges.values():
        edge["amount"] = str(edge["amount"])
    return {"nodes": list(accounts.values()), "edges": list(edges.values()), "priorities": priorities}
