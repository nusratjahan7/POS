import {
  BarChart3,
  Boxes,
  FolderTree,
  LayoutDashboard,
  Package,
  Receipt,
  ScanLine,
  Settings,
  ShieldCheck,
  Tag,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  /** `planned` renders as a disabled affordance — no route exists for it yet. */
  status: "available" | "planned";
  /**
   * Permission required to see this entry. Omit for pages any signed-in user may
   * reach. Purely a visibility filter — the API re-checks server-side.
   */
  permission?: string;
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

/**
 * Single source of truth for primary navigation. Entries are filtered against the
 * signed-in user's permissions, so a Cashier never sees staff administration.
 */
export const navGroups: NavGroup[] = [
  {
    label: "Operations",
    items: [
      { title: "Dashboard", href: "/", icon: LayoutDashboard, status: "available" },
      { title: "Register", href: "/register", icon: ScanLine, status: "planned", permission: "sales:create" },
      { title: "Sales", href: "/sales", icon: Receipt, status: "planned", permission: "sales:read" },
      { title: "Products", href: "/products", icon: Package, status: "available", permission: "catalog:read" },
      { title: "Categories", href: "/categories", icon: FolderTree, status: "available", permission: "catalog:read" },
      { title: "Brands", href: "/brands", icon: Tag, status: "available", permission: "catalog:read" },
      { title: "Inventory", href: "/inventory", icon: Boxes, status: "planned", permission: "inventory:read" },
      { title: "Customers", href: "/customers", icon: Users, status: "planned", permission: "customers:read" },
    ],
  },
  {
    label: "Insight",
    items: [
      { title: "Reports", href: "/reports", icon: BarChart3, status: "planned", permission: "reports:view" },
    ],
  },
  {
    label: "Administration",
    items: [
      { title: "Users", href: "/users", icon: Users, status: "available", permission: "users:read" },
      { title: "Roles", href: "/roles", icon: ShieldCheck, status: "available", permission: "roles:read" },
      { title: "Settings", href: "/settings", icon: Settings, status: "available", permission: "settings:read" },
    ],
  },
];
