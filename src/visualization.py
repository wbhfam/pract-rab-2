"""Текст Graphviz DOT и ASCII-дерево без графических библиотек."""

import json


def to_dot(graph):
    """Сформировать DOT, включая листья, общий узел и циклические рёбра."""
    lines = ["digraph dependencies {"]
    for node in graph:
        lines.append(f"  {json.dumps(node)};")
    for node, children in graph.items():
        for child in children:
            lines.append(f"  {json.dumps(node)} -> {json.dumps(child)};")
    lines.append("}")
    return "\n".join(lines)


def to_ascii(root, graph):
    """Вывести ASCII-дерево; повторные узлы и циклы не раскрывать заново."""
    lines = [root]
    seen = {root}

    def visit(node, prefix, active):
        """Раскрыть детей, сохраняя ветки и показывая тип повторения."""
        children = graph[node]
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "`-- " if last else "|-- "
            marker = " [cycle]" if child in active else ""
            if not marker and child in seen:
                marker = " [shared]"
            lines.append(prefix + branch + child + marker)
            if marker:
                continue
            seen.add(child)
            indent = "    " if last else "|   "
            visit(child, prefix + indent, active | {child})

    visit(root, "", {root})
    return "\n".join(lines)
