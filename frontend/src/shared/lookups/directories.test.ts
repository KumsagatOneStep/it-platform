import { reasonFits } from "./directories";

test("причина подходит к составу операции", () => {
  expect(reasonFits("both", { assets: true, stock: true })).toBe(true);
  expect(reasonFits("assets", { assets: true, stock: false })).toBe(true);
  expect(reasonFits("assets", { assets: true, stock: true })).toBe(false);
  expect(reasonFits("stock", { assets: false, stock: true })).toBe(true);
  expect(reasonFits("stock", { assets: true, stock: false })).toBe(false);
});
