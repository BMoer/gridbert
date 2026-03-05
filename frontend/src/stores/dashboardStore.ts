import { create } from "zustand";
import {
  getWidgets,
  getUserFiles,
  getUserMemory,
  type Widget,
  type UserFile,
  type MemoryFact,
} from "../api/client";

interface DashboardState {
  widgets: Widget[];
  userFiles: UserFile[];
  userMemory: MemoryFact[];
  loaded: boolean;

  /** Fetch widgets, files, and memory from API. */
  loadAll: () => Promise<void>;

  /** Add a widget from SSE event. */
  addWidget: (widget: Widget) => void;

  /** Update an existing widget from SSE event. */
  updateWidget: (widget: Widget) => void;

  /** Refresh just files and memory (after upload or memory update). */
  refreshContext: () => Promise<void>;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  widgets: [],
  userFiles: [],
  userMemory: [],
  loaded: false,

  loadAll: async () => {
    try {
      const [widgets, files, memory] = await Promise.all([
        getWidgets(),
        getUserFiles(),
        getUserMemory(),
      ]);
      set({ widgets, userFiles: files, userMemory: memory, loaded: true });
    } catch {
      set({ loaded: true }); // still mark loaded so UI renders
    }
  },

  addWidget: (widget) =>
    set((s) => ({ widgets: [...s.widgets, widget] })),

  updateWidget: (widget) =>
    set((s) => ({
      widgets: s.widgets.map((w) =>
        w.widget_type === widget.widget_type ? { ...w, ...widget } : w,
      ),
    })),

  refreshContext: async () => {
    try {
      const [files, memory] = await Promise.all([
        getUserFiles(),
        getUserMemory(),
      ]);
      set({ userFiles: files, userMemory: memory });
    } catch {
      // ignore
    }
  },
}));
