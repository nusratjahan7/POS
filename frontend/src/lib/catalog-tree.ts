import type { CategoryNode } from "@/lib/api/catalog";

export type FlatCategory = {
  id: string;
  name: string;
  depth: number;
};

/** Depth-first flatten, so a select can render the hierarchy with indentation. */
export function flattenCategoryTree(nodes: CategoryNode[], depth = 0): FlatCategory[] {
  const flattened: FlatCategory[] = [];
  for (const node of nodes) {
    flattened.push({ id: node.id, name: node.name, depth });
    flattened.push(...flattenCategoryTree(node.children, depth + 1));
  }
  return flattened;
}

/** The ids of a node and every category beneath it (used to block cycles in the UI). */
export function descendantIds(nodes: CategoryNode[], targetId: string): Set<string> {
  const ids = new Set<string>();

  function walk(list: CategoryNode[], collecting: boolean) {
    for (const node of list) {
      const inside = collecting || node.id === targetId;
      if (inside) ids.add(node.id);
      walk(node.children, inside);
    }
  }

  walk(nodes, false);
  return ids;
}
