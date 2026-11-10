"""Renders PPTX slides into PNG images using aspose.slides to verify layout, contrast, and text wrapping."""

from pathlib import Path
import aspose.slides as slides


def render_pptx_to_images(pptx_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    with slides.Presentation(str(pptx_path)) as presentation:
        for idx, slide in enumerate(presentation.slides):
            img = slide.get_image(1.5, 1.5)
            out_img_path = output_dir / f"slide_{idx+1:02d}.png"
            img.save(str(out_img_path))
            print(f"Rendered: {out_img_path}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    pptx_file = project_root / "korea" / "report" / "LG_SC_Korea_ROI_Report.pptx"
    out_dir = project_root / "korea" / "report" / "pptx_snapshots"
    if pptx_file.exists():
        render_pptx_to_images(pptx_file, out_dir)
    else:
        print(f"PPTX file not found at {pptx_file}")
