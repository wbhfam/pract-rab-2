"""Порядок загрузки: зависимости раньше зависящих от них пакетов."""


def loading_order(root, graph):
    """Рекурсивный DFS postorder; при цикле допустимого порядка нет."""
    done = set()
    active = set()
    path = []
    result = []

    def visit(node):
        """Обойти зависимости и добавить пакет после них."""
        if node in active:
            cycle = path[path.index(node):] + [node]
            raise ValueError("Цикл: " + " -> ".join(cycle))
        if node in done:
            return
        active.add(node)
        path.append(node)
        for child in graph[node]:
            visit(child)
        path.pop()
        active.remove(node)
        done.add(node)
        result.append(node)

    visit(root)
    return result
