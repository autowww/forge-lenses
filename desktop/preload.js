/**
 * Exposes a small, read-only API for the Lenses Studio window (frameless chrome).
 */
const { contextBridge, ipcRenderer } = require("electron");

function resolveStudioMode() {
  if (
    process.env.LENSES_VIRTUAL_CAMERA_STUDIO === "1" ||
    process.env.LENSES_VIRTUAL_CAMERA_STUDIO === "true"
  ) {
    return "virtual-camera";
  }
  if (
    process.env.LENSES_STUDIO_UI === "1" ||
    process.env.LENSES_STUDIO_UI === "true" ||
    process.env.LENSES_ENTERPRISE_UI === "1" ||
    process.env.LENSES_ENTERPRISE_UI === "true"
  ) {
    return "studio";
  }
  return null;
}

contextBridge.exposeInMainWorld("lensesElectron", {
  studioMode: resolveStudioMode(),
  minimize: () => ipcRenderer.invoke("win-minimize"),
  maximize: () => ipcRenderer.invoke("win-maximize"),
  close: () => ipcRenderer.invoke("win-close"),
  isMaximized: () => ipcRenderer.invoke("win-is-maximized"),
  platform: process.platform,
  onMaximizedChange: (callback) => {
    if (typeof callback !== "function") return () => {};
    const handler = (_event, maximized) => {
      callback(!!maximized);
    };
    ipcRenderer.on("win-maximized-changed", handler);
    return () => {
      ipcRenderer.removeListener("win-maximized-changed", handler);
    };
  },
});
