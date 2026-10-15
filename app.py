import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from bs4 import BeautifulSoup

sys.setrecursionlimit(20000)

shape_ids = {}
shapes = {}
renames = defaultdict(Counter)


def beautify(source_path, pretty_path):
    with open(source_path, encoding="utf-8") as f:
        pretty_html = BeautifulSoup(f.read(), "html.parser").prettify()
    with open(pretty_path, "w", encoding="utf-8") as f:
        f.write(pretty_html)
    return BeautifulSoup(pretty_html, "html.parser")


def children(element):
    return element.find_all(recursive=False)


def compute_shapes(element):
    key = (element.name, tuple(compute_shapes(child) for child in children(element)))
    shapes[id(element)] = shape_ids.setdefault(key, len(shape_ids))
    return shapes[id(element)]


def pair_children(old_children, new_children):
    matcher = SequenceMatcher(
        None,
        [shapes[id(child)] for child in old_children],
        [shapes[id(child)] for child in new_children],
        autojunk=False,
    )
    for op, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if op in ("equal", "replace"):
            pairs = zip(old_children[old_start:old_end], new_children[new_start:new_end])
            for old_child, new_child in pairs:
                if old_child.name == new_child.name:
                    yield old_child, new_child


def collect_renames(old_element, new_element):
    old_classes = old_element.get("class", [])
    new_classes = new_element.get("class", [])
    removed = [name for name in old_classes if name not in new_classes]
    added = [name for name in new_classes if name not in old_classes]
    for old_name, new_name in zip(removed, added):
        renames[old_name][new_name] += 1
    for old_child, new_child in pair_children(children(old_element), children(new_element)):
        collect_renames(old_child, new_child)


def read_names(path):
    with open(path, encoding="utf-8") as f:
        tokens = f.read().split()
    tokens = [token for token in tokens if not re.fullmatch(r"\d+[.):\-]*", token)]
    return [re.sub(r"^\d+[.):\-]+", "", token) for token in tokens]


def main():
    old_dom = beautify("old.html", "old.pretty.html")
    new_dom = beautify("new.html", "new.pretty.html")
    compute_shapes(old_dom)
    compute_shapes(new_dom)
    collect_renames(old_dom, new_dom)

    names = read_names("mapped.txt")
    mapping = {name: renames[name].most_common(1)[0][0] for name in names if name in renames}
    with open("map.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)
    print(f"{len(mapping)}/{len(names)} mapped")


if __name__ == "__main__":
    main()