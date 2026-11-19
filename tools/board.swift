// 絵コンテの一覧を 1 枚の画像にする(画像を格子に並べ、下に文字を入れる)。
//   swift tools/board.swift spec.json
// spec.json: {"out": "docs/short/storyboard.jpg", "title": "...", "cols": 6, "cell_w": 300,
//             "items": [{"img": "render/short_board/s01.jpg", "lines": ["01  0.0–2.5 秒", "夜 急降下", "20 mm"]}]}
import AppKit
import Foundation

struct Item: Decodable { let img: String; let lines: [String] }
struct Spec: Decodable { let out: String; let title: String; let cols: Int; let cell_w: Int; let items: [Item] }

let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let spec = try JSONDecoder().decode(Spec.self, from: data)

let cw = CGFloat(spec.cell_w)
let ch = cw * 1920.0 / 1080.0
let pad: CGFloat = 18
let textH: CGFloat = 92
let titleH: CGFloat = 70
let rows = (spec.items.count + spec.cols - 1) / spec.cols
let W = Int(CGFloat(spec.cols) * (cw + pad) + pad)
let H = Int(titleH + CGFloat(rows) * (ch + textH + pad) + pad)

let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: W, pixelsHigh: H, bitsPerSample: 8, samplesPerPixel: 4,
                           hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSColor(calibratedWhite: 0.07, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: W, height: H).fill()

func font(_ size: CGFloat, bold: Bool = false) -> NSFont {
    NSFont(name: bold ? "HiraginoSans-W6" : "HiraginoSans-W3", size: size) ?? NSFont.systemFont(ofSize: size)
}
let title: [NSAttributedString.Key: Any] = [.font: font(30, bold: true), .foregroundColor: NSColor.white]
(spec.title as NSString).draw(at: NSPoint(x: pad, y: CGFloat(H) - titleH + 16), withAttributes: title)

for (i, it) in spec.items.enumerated() {
    let r = i / spec.cols, c = i % spec.cols
    let x = pad + CGFloat(c) * (cw + pad)
    let yTop = CGFloat(H) - titleH - CGFloat(r) * (ch + textH + pad)
    if let img = NSImage(contentsOfFile: it.img) {
        img.draw(in: NSRect(x: x, y: yTop - ch, width: cw, height: ch))
    }
    // 下の 4 分の 1 と右端(ショートの画面で隠れる所)を薄く示す
    NSColor(calibratedRed: 1, green: 0.3, blue: 0.2, alpha: 0.55).setStroke()
    let guide = NSBezierPath()
    guide.lineWidth = 1.2
    guide.setLineDash([5, 4], count: 2, phase: 0)
    guide.move(to: NSPoint(x: x, y: yTop - ch * 0.75)); guide.line(to: NSPoint(x: x + cw * 0.86, y: yTop - ch * 0.75))
    guide.line(to: NSPoint(x: x + cw * 0.86, y: yTop))
    guide.stroke()
    for (k, line) in it.lines.enumerated() {
        let a: [NSAttributedString.Key: Any] = [.font: font(k == 0 ? 19 : 15, bold: k == 0),
                                                .foregroundColor: k == 0 ? NSColor.white : NSColor(calibratedWhite: 0.78, alpha: 1)]
        (line as NSString).draw(at: NSPoint(x: x, y: yTop - ch - 28 - CGFloat(k) * 22), withAttributes: a)
    }
}
NSGraphicsContext.restoreGraphicsState()
let jpg = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.9])!
try jpg.write(to: URL(fileURLWithPath: spec.out))
print("[board] 保存 \(spec.out)(\(W)×\(H))")
