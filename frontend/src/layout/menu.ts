import {
  IconBook2,
  IconBuildingCommunity,
  IconLayoutDashboard,
  IconUserCircle,
  IconUsers,
} from "@tabler/icons-react";
import type { ComponentType } from "react";

import type { UserRole } from "../api/types";

export interface MenuItem {
  label: string;
  to: string;
  icon: ComponentType<{ size?: string | number; stroke?: string | number }>;
}

export interface MenuSection {
  title?: string;
  roles?: readonly UserRole[];
  items: MenuItem[];
}

export const MENU: readonly MenuSection[] = [
  {
    items: [
      { label: "Главная", to: "/", icon: IconLayoutDashboard },
      { label: "Профиль", to: "/profile", icon: IconUserCircle },
    ],
  },
  {
    title: "Администрирование",
    roles: ["admin"],
    items: [
      { label: "Пользователи", to: "/admin/users", icon: IconUsers },
      { label: "Отделы", to: "/admin/departments", icon: IconBuildingCommunity },
      { label: "Справочники", to: "/admin/directories", icon: IconBook2 },
    ],
  },
];

export function menuForRole(role: UserRole): MenuSection[] {
  return MENU.filter((section) => !section.roles || section.roles.includes(role));
}
