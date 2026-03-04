import { useEffect, useState } from "react";
import { getWidgets, type Widget } from "../../api/client";
import { getWidgetComponent, getWidgetLabel } from "./WidgetRegistry";

export function DashboardGrid() {
  const [widgets, setWidgets] = useState<Widget[]>([]);

  useEffect(() => {
    getWidgets()
      .then(setWidgets)
      .catch(() => {
        /* ignore — no widgets yet */
      });
  }, []);

  if (widgets.length === 0) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {widgets.map((widget) => {
        const Component = getWidgetComponent(widget.widget_type);
        if (!Component) {
          return (
            <div
              key={widget.id}
              className="rounded-xl bg-white p-5 shadow-sm border border-gray-100"
            >
              <p className="text-sm text-gray-400">
                Widget: {getWidgetLabel(widget.widget_type)}
              </p>
            </div>
          );
        }
        return <Component key={widget.id} config={widget.config} />;
      })}
    </div>
  );
}
