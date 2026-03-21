import tkinter as tk

BG3     = "#1a1a2e"
CYAN    = "#00f5ff"
MAGENTA = "#ff00ff"
DIM     = "#444466"

def draw_sparkline(canvas, samples: list, width: int, height: int, mini=False):
    canvas.delete("all")
    canvas.configure(bg=BG3)

    if not samples:
        canvas.create_text(width//2, height//2,
            text="NO DATA YET", fill=DIM,
            font=("Courier New", 8))
        return

    pad_x = 8  if mini else 40
    pad_y = 6  if mini else 20
    graph_w = width  - (pad_x * 2)
    graph_h = height - (pad_y * 2)

    min_v = min(samples)
    max_v = max(samples) if max(samples) != min_v else min_v + 1

    def to_x(i):
        return pad_x + (i / max(len(samples) - 1, 1)) * graph_w

    def to_y(v):
        return pad_y + graph_h - ((v - min_v) / (max_v - min_v)) * graph_h

    # Grid lines
    for i in range(3):
        y = pad_y + (graph_h / 2) * i
        canvas.create_line(pad_x, y, pad_x + graph_w, y, fill=DIM, dash=(2,4))

    # Fill area — solid dark color instead of transparent
    if len(samples) > 1:
        points = []
        for i, v in enumerate(samples):
            points.extend([to_x(i), to_y(v)])
        points.extend([to_x(len(samples)-1), pad_y + graph_h])
        points.extend([to_x(0), pad_y + graph_h])
        canvas.create_polygon(points, fill="#0a1a2a", outline="")

    # Line
    if len(samples) > 1:
        for i in range(len(samples) - 1):
            canvas.create_line(
                to_x(i),   to_y(samples[i]),
                to_x(i+1), to_y(samples[i+1]),
                fill=CYAN, width=2, smooth=True)

    # Last point dot
    lx = to_x(len(samples)-1)
    ly = to_y(samples[-1])
    r  = 3 if mini else 5
    canvas.create_oval(lx-r, ly-r, lx+r, ly+r, fill=MAGENTA, outline="")

    if not mini:
        canvas.create_text(pad_x-4, pad_y,
            text=f"{max_v:.0f}", fill=DIM, font=("Courier New", 7), anchor="e")
        canvas.create_text(pad_x-4, pad_y+graph_h,
            text=f"{min_v:.0f}", fill=DIM, font=("Courier New", 7), anchor="e")
        canvas.create_text(pad_x-4, pad_y+graph_h//2,
            text="ms", fill=DIM, font=("Courier New", 7), anchor="e")
        canvas.create_text(pad_x, pad_y+graph_h+10,
            text="60s ago", fill=DIM, font=("Courier New", 7), anchor="w")
        canvas.create_text(pad_x+graph_w, pad_y+graph_h+10,
            text="now", fill=DIM, font=("Courier New", 7), anchor="e")
        canvas.create_text(width-pad_x, pad_y-8,
            text=f"LATEST: {samples[-1]} ms", fill=CYAN,
            font=("Courier New", 8, "bold"), anchor="e")
