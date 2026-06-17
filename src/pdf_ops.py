from pypdf import PdfReader, PdfWriter
import fitz
import os

async def merge_pdfs(input_paths: list[str], output_path: str) -> str | None:
    try:
        writer = PdfWriter()
        for p in input_paths:
            writer.append(p)
        with open(output_path, "wb") as f:
            writer.write(f)
        writer.close()
        return output_path
    except Exception as e:
        print(f"[merge_pdfs] {e}")
        return None

async def split_pdf(input_path: str, output_dir: str, pages_per_file: int = 1) -> list[str]:
    try:
        reader = PdfReader(input_path)
        total = len(reader.pages)
        output_paths = []

        for start in range(0, total, pages_per_file):
            writer = PdfWriter()
            end = min(start + pages_per_file, total)
            for i in range(start, end):
                writer.add_page(reader.pages[i])
            name = os.path.join(output_dir, f"part_{start // pages_per_file + 1}.pdf")
            with open(name, "wb") as f:
                writer.write(f)
            writer.close()
            output_paths.append(name)

        return output_paths
    except Exception as e:
        print(f"[split_pdf] {e}")
        return []

async def rotate_pdf(input_path: str, output_path: str, degrees: int = 90) -> str | None:
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(degrees)
            writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        writer.close()
        return output_path
    except Exception as e:
        print(f"[rotate_pdf] {e}")
        return None

async def compress_pdf(input_path: str, output_path: str) -> str | None:
    try:
        doc = fitz.open(input_path)
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        return output_path
    except Exception as e:
        print(f"[compress_pdf] {e}")
        return None

async def pdf_to_images(input_path: str, output_dir: str, dpi: int = 200) -> list[str]:
    try:
        doc = fitz.open(input_path)
        paths = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            out = os.path.join(output_dir, f"page_{i+1}.png")
            pix.save(out)
            paths.append(out)
        doc.close()
        return paths
    except Exception as e:
        print(f"[pdf_to_images] {e}")
        return []

async def add_watermark(input_path: str, output_path: str, text: str) -> str | None:
    try:
        doc = fitz.open(input_path)
        for page in doc:
            rect = page.rect
            w, h = rect.width, rect.height
            page.insert_text(
                (w * 0.3, h * 0.5),
                text,
                fontsize=48,
                color=(0.7, 0.7, 0.7),
            )
        doc.save(output_path)
        doc.close()
        return output_path
    except Exception as e:
        print(f"[watermark] {e}")
        return None

async def encrypt_pdf(input_path: str, output_path: str, password: str) -> str | None:
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        with open(output_path, "wb") as f:
            writer.write(f)
        writer.close()
        return output_path
    except Exception as e:
        print(f"[encrypt_pdf] {e}")
        return None

async def decrypt_pdf(input_path: str, output_path: str, password: str) -> str | None:
    try:
        reader = PdfReader(input_path)
        if not reader.is_encrypted:
            return None
        reader.decrypt(password)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        writer.close()
        return output_path
    except Exception as e:
        print(f"[decrypt_pdf] {e}")
        return None
