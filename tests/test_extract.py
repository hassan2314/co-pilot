from app.extract import UploadError, clean_filename, prepare_upload


def test_clean_filename_strips_directories():
    assert clean_filename("../../pto policy.md") == "pto policy.md"


def test_prepare_txt_and_markdown():
    path, kind, text = prepare_upload("notes.TXT", b"\xef\xbb\xbfHello handbook")
    assert path == "notes.TXT"
    assert kind == "txt"
    assert text == "Hello handbook"

    path, kind, text = prepare_upload("guide.markdown", b"# Title\n\nBody")
    assert kind == "md"
    assert "Title" in text


def test_rejects_unknown_type_and_empty():
    try:
        prepare_upload("virus.exe", b"hello")
        raise AssertionError("expected rejection")
    except UploadError as exc:
        assert exc.code == 415

    try:
        prepare_upload("empty.txt", b"")
        raise AssertionError("expected rejection")
    except UploadError as exc:
        assert exc.code == 400


def test_pdf_text_roundtrip():
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.multi_cell(0, 8, "ACME employees may work from home three days each week.")
    data = bytes(pdf.output())
    path, kind, text = prepare_upload("remote-work.pdf", data)
    assert path == "remote-work.pdf"
    assert kind == "pdf"
    assert "three days" in text
