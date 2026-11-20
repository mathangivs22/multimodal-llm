// "system" follows the device's dark-mode setting; "light"/"dark" override it.
// The choice is applied as data-theme on <html> (index.html also applies it before
// the first paint, so there's no flash of the wrong theme).
const KEY = "meetingiq-theme";
export const THEMES = ["system", "light", "dark"];

export function getTheme() {
  try {
    const value = localStorage.getItem(KEY);
    return THEMES.includes(value) ? value : "system";
  } catch {
    return "system";
  }
}

export function setTheme(theme) {
  const root = document.documentElement;
  if (theme === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme);
  try {
    if (theme === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, theme);
  } catch {
    // Storage blocked (private mode): the choice lasts until the page is closed
  }
}
