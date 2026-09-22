import {
  IconArrowsExchange,
  IconBook2,
  IconBuildingCommunity,
  IconDeviceLaptop,
  IconHistory,
  IconLayoutDashboard,
  IconPackage,
  IconUserCircle,
  IconUsers,
} from "@tabler/icons-react";
import type { ComponentType } from "react";

import type { UserRole } from "../api/types";

export interface MenuItem {
  label: string;
  to: string;
  icon: ComponentType<{ size?: string | number; stroke?: string | number }>;
  roles?: readonly UserRole[];
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
    title: "Склад и техника",
    items: [
      { label: "Реестр техники", to: "/equipment/assets", icon: IconDeviceLaptop },
      { label: "Расходники", to: "/equipment/stock", icon: IconPackage, roles: ["admin"] },
      {
        label: "История движений",
        to: "/equipment/movements",
        icon: IconHistory,
        roles: ["admin"],
      },
      {
        label: "Выдать / принять",
        to: "/equipment/issue",
        icon: IconArrowsExchange,
        roles: ["admin"],
      },
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

const allowed = (roles: readonly UserRole[] | undefined, role: UserRole) =>
  !roles || roles.includes(role);

export function menuForRole(role: UserRole): MenuSection[] {
  return MENU.filter((section) => allowed(section.roles, role)).map((section) => ({
    ...section,
    items: section.items.filter((item) => allowed(item.roles, role)),
  }));
}
