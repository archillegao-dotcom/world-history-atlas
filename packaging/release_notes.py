"""Release notes for the standalone zips.  python packaging/release_notes.py DIR"""
import plistlib
import sys
import zipfile
from pathlib import Path


def _plist(zpath):
    with zipfile.ZipFile(zpath) as zf:
        names = [
            n for n in zf.namelist()
            if n.endswith("WorldHistoryAtlas.app/Contents/Info.plist")
            and "/._" not in n and not Path(n).name.startswith("._")
        ]
        if not names:
            return {}
        return plistlib.loads(zf.read(names[0]))


def _mb(path):
    return f"{path.stat().st_size / 1e6:.0f} MB"


def main():
    folder = Path(sys.argv[1])
    lines = [
        "## v0.6.1 更新（2026-11-02）",
        "",
        "这是 v0.5.0 之后的第一次发布，包含 v0.6.0 的地图改动和 v0.6.1 的修正。已知缺口见 [KNOWN_ISSUES.md](https://github.com/archillegao-dotcom/world-history-atlas/blob/v0.6.1/KNOWN_ISSUES.md)。",
        "",
        "- **空位期、摄政与共治**：君主空缺或年幼时，「领导人」顶部显示实际掌权者，并标注共治、摄政、权臣、临时执政或对立君主（103 个个案，每条附来源）。例如周共和行政（前 841–前 828）、霍光、吕后、曹操、武则天、张居正、鳌拜，以及神圣罗马帝国大空位、奥斯曼空位期、匈牙利摄政霍尔蒂等。",
        "- **君主空档**：225 处逐条核对。补入缺失君主 45 处；确认真实空位、摄政或共治 66 处；109 处是日期精度或扫描假象；5 处无法核实，标为「未记录」。只精确到年的长期在位记录，不再被前任的精确就任日整段截掉。",
        "- **默认政权**：同一区域有多个候选时，优先打开这一天有在位者或空位期案例、时段更具体的政权（如 430 年「波斯」→ 萨珊王朝），并可以切换回去。柔佛、霹雳、雪兰莪、日惹苏丹国可以单独点击。",
        "- **补充职位**：幕府将军、关白、摄政、执权、护国公，以及北洋政府大总统与国务总理（1912–1928）。",
        "- **中文名**：用 Wikidata 中文标签、中文维基和英文维基的中文链接补译，底图名称经过人工复核。没有通用译名的显示原名并注明「（暂无通用译名）」；夹着英文残片的机器翻译不再显示。",
        "- **修正**：中华人民共和国面板不再同时列出中华民国（宪政）；马来西亚首都不再显示成「、吉隆坡」；面板标题去掉括号里的英文。巴林、瑙鲁显示中文名。1950 年的科威特、莱恩群岛、多米尼克、圣卢西亚、圣文森特、圣基茨可以点击并显示当时的殖民地归属。世界尺度下点梵蒂冈、澳门不再选到意大利、香港。补上 1942-11 至 1943-09 意大利在法国的占领区（按省近似），以及 1939-10-15 华沙的德军军事管理区。并发请求同一边界不再把服务器打崩。退化成线或点的过渡边界不再让整张地图点不了。点到控制区标签也会选中下面的政权。",
        "- **v0.6.0（此前未单独发布）**：1886 年以后的边界改用 CShapes 2.0；二战欧洲用 Stanford 月度占领区；中日战争与太平洋按实际控制区显示；1800 年以后只写到年份的起止不再放宽 ±1 年。",
        "",
        "免安装版，不需要安装 Python。请先解压再运行，不要在压缩包里直接双击。",
        "",
        "历史地图数据在软件包里，只读。每天自动更新的新闻和维基百科缓存写在个人目录：",
        "macOS `~/Library/Application Support/WorldHistoryAtlas`，Windows `%APPDATA%\\WorldHistoryAtlas`。",
        "",
        "## macOS",
        "",
        "软件没有 Apple 开发者签名，也没有公证。从浏览器下载后，macOS 会拦截第一次打开（这是正常的，不是文件坏了）：",
        "",
        "1. 在访达里 **按住 Control 点按** `WorldHistoryAtlas.app` → 选“打开” → 在弹窗里再点“打开”。",
        "2. 如果弹窗里没有“打开”（macOS 15 / 26 上常见）：先双击一次让系统拦住它，然后打开 **系统设置 → 隐私与安全性**，点“仍要打开”。",
        "3. 只需做一次。若提示“已损坏”，在终端执行 `xattr -dr com.apple.quarantine` 加上 App 的路径，然后再打开。",
        "",
        "双击后通常会打开“终端”窗口并自动打开浏览器。有这个窗口时，不要关闭它，关掉就是退出。",
        "",
        "从「下载」文件夹直接打开时，macOS 会把 App 放到临时目录。这时不再转去终端（否则会报找不到文件），软件在后台运行并打开浏览器。退出请点网页右上角的「退出」，或打开 http://localhost:8790/quit 。不要去运行个人文件夹里旧的 launch.command。",
        "",
    ]
    mac = sorted(folder.glob("WorldHistoryAtlas-macos-*.zip"))
    if not mac:
        lines.append("（这次没有 macOS 压缩包。）")
    if not any("arm64" in z.name for z in mac):
        lines.append("这次没有 Apple 芯片专用包：GitHub 的 arm64 构建机器把还在排队的任务取消了。请先用下面的 Intel 包，Apple 芯片的 Mac 可以通过 Rosetta 2 打开它。")
        lines.append("")
    for z in mac:
        minos = _plist(z).get("LSMinimumSystemVersion") or "见 App 的最低系统版本"
        if "arm64" in z.name:
            who = f"仅 Apple 芯片（M1/M2/M3/M4）。需要 macOS {minos} 或更高。不能在 Intel Mac 上运行。"
        elif "x64" in z.name:
            who = (f"Intel Mac，以及通过 Rosetta 2 运行的 Apple 芯片 Mac。"
                   f"需要 macOS {minos} 或更高。")
        else:
            who = f"需要 macOS {minos} 或更高。"
        lines.append(f"- `{z.name}`（{_mb(z)}）：{who}")
    lines += ["", "## Windows", ""]
    wins = sorted(folder.glob("WorldHistoryAtlas-windows-*.zip"))
    if wins:
        for z in wins:
            lines.append(
                f"- `{z.name}`（{_mb(z)}）：Windows 10/11 64 位。"
                "SmartScreen 若提示“Windows 已保护你的电脑”，点“更多信息”→“仍要运行”。"
            )
    else:
        lines.append("Windows 压缩包会在 Windows 构建成功后附加到这个 Release。Windows 失败不会撤下上面的 macOS 包。")
    lines.append("")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
