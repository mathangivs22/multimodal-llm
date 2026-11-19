import { App as CapacitorApp } from "@capacitor/app";
import { Capacitor } from "@capacitor/core";

/** Phone-app behaviour that the website doesn't need. */
export function setUpNativeShell() {
  if (!Capacitor.isNativePlatform()) return;
  document.documentElement.classList.add("native", `native-${Capacitor.getPlatform()}`);

  // Android's back button goes back a page, and leaves the app from the first page
  CapacitorApp.addListener("backButton", ({ canGoBack }) => {
    if (canGoBack) window.history.back();
    else CapacitorApp.exitApp();
  });
}
