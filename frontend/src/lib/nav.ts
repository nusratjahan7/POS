import {
  Banknote,
  BarChart3,
  Boxes,
  Calculator,
  FolderTree,
  HandCoins,
  LayoutDashboard,
  Package,
  Receipt,
  ScanLine,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Tag,
  Truck,
  Users,
  Wallet,
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
      { title: "Register", href: "/register", icon: ScanLine, status: "available", permission: "sales:create" },
      { title: "Sales", href: "/sales", icon: Receipt, status: "available", permission: "sales:read" },
      { title: "Products", href: "/products", icon: Package, status: "available", permission: "catalog:read" },
      { title: "Categories", href: "/categories", icon: FolderTree, status: "available", permission: "catalog:read" },
      { title: "Brands", href: "/brands", icon: Tag, status: "available", permission: "catalog:read" },
      { title: "Inventory", href: "/inventory", icon: Boxes, status: "available", permission: "inventory:read" },
      { title: "Suppliers", href: "/suppliers", icon: Truck, status: "available", permission: "suppliers:read" },
      { title: "Purchases", href: "/purchases", icon: ShoppingCart, status: "available", permission: "purchases:view" },
      { title: "Customers", href: "/customers", icon: Users, status: "available", permission: "customers:read" },
      { title: "Customer Dues", href: "/dues/customers", icon: Wallet, status: "available", permission: "customers:read" },
      { title: "Supplier Dues", href: "/dues/suppliers", icon: HandCoins, status: "available", permission: "suppliers:read" },
      { title: "Expenses", href: "/expenses", icon: Banknote, status: "available", permission: "expenses:read" },
      { title: "Cash Sessions", href: "/cash-sessions", icon: Calculator, status: "available", permission: "registers:read" },
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
