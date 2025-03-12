import requests

def download_pdf(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {save_path}")
    else:
        print(f"Failed to download {url}, Status Code: {response.status_code}")

# Example: Download multiple PDFs with a predictable pattern
base_url = "https://example.com/reports/report_{}.pdf"  # Modify as needed
for i in range(1, 6):  # Change range for more files
    pdf_url = base_url.format(i)  # Generates URLs like report_1.pdf, report_2.pdf, ...
    save_path = f"report_{i}.pdf"
    download_pdf(pdf_url, save_path)
