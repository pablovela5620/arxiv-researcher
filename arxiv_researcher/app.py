import json
import gradio as gr
import requests
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Dict

from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.docstore.base import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter

CHAT_MODEL = ChatOpenAI(model="gpt-3.5-turbo-16k")


def download_pdf_from_url(pdf_link: str) -> str:
    # Generate a unique filename
    unique_filename = f"input/downloaded_paper_{uuid.uuid4().hex}.pdf"

    # Send a GET request to the PDF link
    response = requests.get(pdf_link)

    if response.status_code == 200:
        # Save the PDF content to a local file
        with open(unique_filename, "wb") as pdf_file:
            pdf_file.write(response.content)
        print("PDF downloaded successfully.")
    else:
        print("Failed to download the PDF.")
    return unique_filename


def nougat_ocr(file_path: Path) -> None:
    assert file_path.exists(), f"File {file_path} does not exist"
    # unique_filename = f"/content/output/downloaded_paper_{uuid.uuid4().hex}.pdf"
    # Runs nougat OCR on the file and saves the output to the output folder as a .mmd file
    cli_command = [
        "nougat",
        "--out",
        "output",
        "pdf",
        f"{str(file_path)}",
        "--markdown",
    ]

    # Run the command and capture its output
    subprocess.run(
        cli_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return


def pdf_to_mmd(
    pdf_file: Optional[str],
    pdf_link: str,
    progress=gr.Progress(),
) -> str:
    """
    pdf_file: str the path to the pdf file
    pdf_link: str the link to the pdf file
    """
    # Create the input/output folder if it does not exist
    Path("input").mkdir(parents=True, exist_ok=True)
    Path("output").mkdir(parents=True, exist_ok=True)
    # Either download the pdf file from the link or use the uploaded pdf file
    if pdf_file is None:
        progress(0.0, desc="Downloading PDF file from the link")
        if pdf_link == "":
            return "No data provided. Upload a pdf file or provide a pdf link and try again!"
        else:
            file_name = download_pdf_from_url(pdf_link)
    else:
        progress(0.1, desc="Parsing the uploaded PDF file")
        file_name = "not yet implemented"

    file_path = Path(file_name)
    assert file_path.exists(), f"File {file_path} does not exist"

    # Run the OCR
    progress(
        0.3, desc="Running Nougat OCR on the PDF file - This may take a while (~5 mins)"
    )
    nougat_ocr(file_path)

    progress(0.9, desc="Loading Markdown file")
    markdown_path = Path(f"output/{file_path.stem}.mmd")
    assert markdown_path.exists(), f"File {markdown_path} does not exist"
    with open(markdown_path, "r") as file:
        content = file.read()
    # switch math delimiters for gradio markdown support
    content = (
        content.replace(r"\(", "$")
        .replace(r"\)", "$")
        .replace(r"\[", "$$")
        .replace(r"\]", "$$")
    )
    return content


def create_individual_summmary_chain() -> None:
    prompt_template = """You are being given a markdown document with headers, this is part of a larger arxiv paper. Your task is to write a summary of the document.
    here are the headers of this particlar section of the paper:
    "{headers}"
    and here is the content of the section:
    "{page_content}"
    For the summary provide it in the format of a bullet point list consisting of at minimum 2 bullet points and at most 5.
    It should also be in markdown format
    SUMMARY:"""
    prompt = ChatPromptTemplate.from_template(prompt_template)
    individual_summary_chain = prompt | CHAT_MODEL
    return individual_summary_chain


def create_final_summmary_chain() -> None:
    prompt_template = """You are presented with a collection of text snippets. Each snippet is a summary of a specific section from an academic paper published on arXiv. Your objective is to synthesize these snippets into a coherent, concise summary of the entire paper.

    DOCUMENT SNIPPETS:
    "{docs}"

    INSTRUCTIONS: Craft a concise summary below, capturing the essence of the paper based on the provided snippets.
    It is also important that you highlight the key contributions of the paper, and 3 key takeaways from the paper.
    Lastly you should provide a list of 5 questions that you would ask the author of the paper if you had the chance.
    SUMMARY:
    """
    final_summary_prompt = ChatPromptTemplate.from_template(prompt_template)
    final_summary_chain = final_summary_prompt | CHAT_MODEL

    return final_summary_chain


def generate_individual_summary(parsed_output: str) -> str:
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )
    md_header_splits = markdown_splitter.split_text(parsed_output)

    individual_summary_chain = create_individual_summmary_chain()

    summary_docs = []
    summary = ""
    for split in md_header_splits:
        current_header: Dict[str, str] = json.dumps(split.metadata)
        current_page_content: str = split.page_content

        header_to_append = ""
        for key in split.metadata.keys():
            if key == "Header 3":
                header_to_append = f"\n### {split.metadata[key]}\n"
            elif key == "Header 2":
                header_to_append = f"\n## {split.metadata[key]}\n"
            elif key == "Header 1":
                header_to_append = f"\n# {split.metadata[key]}\n"

        summary += header_to_append
        for s in individual_summary_chain.stream(
            {"headers": current_header, "page_content": current_page_content}
        ):
            summary += s.content
            yield summary

        doc = Document(page_content=current_page_content, metadata=split.metadata)
        summary_docs.append(doc)


def generate_final_summary(individual_summaries: str) -> str:
    final_summary_chain = create_final_summmary_chain()
    final_summary = ""
    for s in final_summary_chain.stream({"docs": individual_summaries}):
        final_summary += s.content
        yield final_summary


def main() -> None:
    css = """
    #mkd {
        height: 500px; 
        overflow: auto; 
        border: 1px solid #ccc; 
    }
    """

    with gr.Blocks(css=css) as demo:
        gr.HTML("<h1><center>🦉 Arxiv Researcher<center><h1>")
        gr.HTML(
            "<h3><center>Uses Nougat OCR and Langchain (GPT-3.5) to generate a summary of provided arxiv link or pdf<center></h3>"
        )

        with gr.Row():
            mkd = gr.Markdown("<h4><center>Upload a PDF</center></h4>", scale=1)
            mkd = gr.Markdown("<h4><center><i>OR</i></center></h4>", scale=1)
            mkd = gr.Markdown("<h4><center>Provide a PDF link</center></h4>", scale=1)

        with gr.Row(equal_height=True):
            pdf_file = gr.File(label="PDF📃", file_count="single", scale=1)
            pdf_link = gr.Textbox(
                placeholder="Enter an Arxiv link here", label="PDF link🔗🌐", scale=1
            )

        with gr.Row():
            btn = gr.Button("Run NOUGAT🍫")
            clr = gr.Button("Clear🚿")

        with gr.Row():
            gr.Markdown(
                "<h3>PDF converted to markup language through Nougat-OCR👇:</h3>"
            )
            gr.Markdown("<h3>Summaries of each section of markdown file👇:</h3>")
            gr.Markdown("<h3>Final Summary of entire Arixv document👇:</h3>")
        with gr.Row():
            parsed_output = gr.Markdown(elem_id="mkd", value="📃🔤OCR Output")
            individual_summary = gr.Markdown(
                elem_id="mkd", value="Individual Summary, wait for OCR to be done..."
            )
            final_summary = gr.Markdown(
                elem_id="mkd",
                value="Overall Summary, wait for all individual summaries to be generated...",
            )

        btn.click(
            fn=pdf_to_mmd,
            inputs=[pdf_file, pdf_link],
            outputs=parsed_output,
        ).success(
            fn=generate_individual_summary,
            inputs=[parsed_output],
            outputs=individual_summary,
        ).success(
            fn=generate_final_summary,
            inputs=[individual_summary],
            outputs=final_summary,
        )
        clr.click(
            fn=lambda: (
                gr.update(value=None),
                gr.update(value=None),
                gr.update(value=None),
            ),
            inputs=[],
            outputs=[pdf_file, pdf_link, parsed_output],
        )

        gr.Examples(
            [[None, "https://arxiv.org/pdf/2308.11417.pdf"]],
            inputs=[pdf_file, pdf_link],
            outputs=parsed_output,
            fn=pdf_to_mmd,
            cache_examples=False,
            label="Click on any Examples below to get Nougat OCR results quickly:",
        )

    demo.queue()
    demo.launch(debug=True)


if __name__ == "__main__":
    main()
