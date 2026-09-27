import {
  BarChart3,
  Boxes,
  LayoutDashboard,
  Package,
  Receipt,
  ScanLine,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  /** `planned` renders as a disabled affordance — no routes exist for it yet. */
  status: "available" | "planned";
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

/**
 * Single source of truth for primary navigation. Items are marked `planned`
 * until the owning module ships, so the shell never links to a dead route.
 */
export const navGroups: NavGroup[] = [
  {
    label: "Operations",
    items: [
      { title: "Dashboard", href: "/", icon: LayoutDashboard, status: "available" },
      { title: "Register", href: "/register", icon: ScanLine, status: "planned" },
      { title: "Sales", href: "/sales", icon: Receipt, status: "planned" },
      { title: "Products", href: "/products", icon: Package, status: "planned" },
      { title: "Inventory", href: "/inventory", icon: Boxes, status: "planned" },
    ],
  },
  {
    label: "Management",
    items: [
      { title: "Customers", href: "/customers", icon: Users, status: "planned" },
      { title: "Reports", href: "/reports", icon: BarChart3, status: "planned" },
      { title: "Settings", href: "/settings", icon: Settings, status: "planned" },
    ],
  },
];
