"""WCAG contrast check for the design tokens in docs/DESIGN.md (text on page, panel and its own 12% pill)."""


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(fg, bg, a):
    return "#" + "".join(f"{round(int(fg[i:i+2], 16) * a + int(bg[i:i+2], 16) * (1 - a)):02X}" for i in (1, 3, 5))


MODES = {
    "light": {"bg": "#F1F0EC", "surface": "#FFFFFF", "text": {"ink": "#1A1C21", "muted": "#585A60", "brass": "#7C5A12",
              "verified": "#1B6646", "review": "#9C3F0B", "assay": "#5B3970"}},
    "dark": {"bg": "#121316", "surface": "#1A1C20", "text": {"ink": "#ECEAE3", "muted": "#A3A39C", "brass": "#D9AE55",
             "verified": "#5CC995", "review": "#F0965A", "assay": "#C9A2DB"}},
}
fails = 0
for mode, t in MODES.items():
    for name, fg in t["text"].items():
        for bgname, bg in (("bg", t["bg"]), ("surface", t["surface"]), ("pill", mix(fg, t["surface"], 0.12))):
            r = ratio(fg, bg)
            fails += r < 4.5
            print(f"{mode:5} {name:8} on {bgname:7} {r:5.2f}{'  FAIL' if r < 4.5 else ''}")
print(f"ink on brass button {ratio('#16181D', '#D9AE55'):.2f}")
print("all pass AA" if not fails else f"{fails} fail")
