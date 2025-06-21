import requests
import fitz  # PyMuPDF
import os
import subprocess
from urllib.parse import urlparse, urlunparse
import re
import sys
import time
import random
from pathlib import Path

def download_pdf(url, save_path, max_retries=3):
    """
    Download a PDF file from the given URL and save it to the specified path.
    Includes browser-like headers and retry logic to overcome 403 errors.
    
    Args:
        url (str): URL of the PDF file to download
        save_path (str): Path where the PDF will be saved
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    # Browser-like headers to avoid 403 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Referer': 'https://www.wimbledon.com/',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
    
    # Check if the file already exists
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        print(f"File already exists at {save_path}, skipping download.")
        return True
    
    # Try to download with retry logic
    retries = 0
    while retries <= max_retries:
        try:
            print(f"Downloading {url} (attempt {retries + 1}/{max_retries + 1})")
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            print(f"Successfully downloaded: {url}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"403 Forbidden error. The site might be blocking automated access.")
                # Try to find a local copy in the scraper directory
                file_name = os.path.basename(save_path)
                scraper_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scraper', file_name)
                
                if os.path.exists(scraper_path):
                    print(f"Found local copy at {scraper_path}, copying to {save_path}")
                    import shutil
                    shutil.copy2(scraper_path, save_path)
                    return True
                    
            elif e.response.status_code == 404:
                print(f"404 Not Found: {url}")
                return False
                
            print(f"HTTP error {e.response.status_code} downloading {url}: {e}")
            
        except Exception as e:
            print(f"Error downloading {url}: {e}")
        
        # If we get here, the download failed, so we'll retry
        retries += 1
        if retries <= max_retries:
            # Exponential backoff with jitter
            wait_time = (2 ** retries) + random.uniform(0, 1)
            print(f"Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)
    
    print(f"Failed to download {url} after {max_retries + 1} attempts")
    return False

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file with improved formatting for Wimbledon tournament data
    using PyMuPDF for better extraction results.
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        str: Simplified and cleaned text from the PDF
    """
    try:
        # Extracted text will be organized into sections
        header_info = []
        first_round_data = []
        second_round_data = []
        third_round_data = []
        qualifiers_data = []
        
        with fitz.open(pdf_path) as pdf:
            # First extract header information from the first page
            if len(pdf) > 0:
                first_page = pdf[0]
                # Get the tournament name, year, and event from the first few blocks
                header_text = first_page.get_text("text").split('\n')[:10]
                for line in header_text:
                    if "Championships" in line or "Qualifying" in line or "Round" in line:
                        header_info.append(line.strip())
            
            # Now process all pages to extract player data
            current_section = None
            
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                text = page.get_text("text")
                if not text:
                    continue
                
                # Split into lines and process each one
                for line in text.split('\n'):
                    line = line.strip()
                    
                    # Skip empty lines and copyright notice
                    if not line or "copyright" in line.lower():
                        continue
                    
                    # Determine which section this line belongs to
                    if "First Round" in line and "Second Round" in line:
                        # This is a header line, skip it
                        continue
                    elif line.startswith("First Round"):
                        current_section = "first"
                        continue
                    elif line.startswith("Second Round"):
                        current_section = "second"
                        continue
                    elif line.startswith("Third Round"):
                        current_section = "third"
                        continue
                    elif line.startswith("Qualifiers"):
                        current_section = "qualifiers"
                        continue
                    
                    # Check if line contains player data (starts with a number or (WC))
                    if re.match(r'^(\d+\.|[(]WC[)]).*', line.strip()):
                        # Clean up the line format for easier parsing
                        # Remove multiple spaces
                        line = re.sub(r'\s{2,}', ' ', line)
                        
                        # Add this line to the appropriate section
                        if current_section == "first":
                            first_round_data.append(line)
                        elif current_section == "second":
                            second_round_data.append(line)
                        elif current_section == "third":
                            third_round_data.append(line)
                        elif current_section == "qualifiers":
                            qualifiers_data.append(line)
                    
                    # Also add lines with match scores (typically start with a player abbrev)
                    elif re.match(r'^[A-Z]\. [A-Za-z]+.*\d+/\d+', line) or re.match(r'^.*\.\.\.\d+/\d+', line):
                        if current_section == "second":
                            second_round_data.append(line)
                        elif current_section == "third":
                            third_round_data.append(line)
                        elif current_section == "qualifiers":
                            qualifiers_data.append(line)
        
        # Build a simplified representation of the tournament data
        # Start with the header
        result_lines = header_info.copy()
        
        # Add section headers and data
        result_lines.append("First Round")
        result_lines.extend(first_round_data)
        
        result_lines.append("Second Round")
        result_lines.extend(second_round_data)
        
        result_lines.append("Third Round")
        result_lines.extend(third_round_data)
        
        result_lines.append("Qualifiers")
        result_lines.extend(qualifiers_data)
        
        return "\n".join(result_lines)
    
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        import traceback
        traceback.print_exc()
        return ""

def increment_year_in_url(url):
    """
    Increment the year in the URL.
    
    Args:
        url (str): URL containing a year to increment
    
    Returns:
        str: URL with incremented year
    """
    # Parse the URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Find and increment the year in the path
    year_pattern = r'/(\d{4})_'
    match = re.search(year_pattern, path)
    
    if match:
        current_year = int(match.group(1))
        next_year = current_year + 1
        new_path = path.replace(f'/{current_year}_', f'/{next_year}_')
        
        # Reconstruct the URL with the new path
        new_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            new_path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))
        
        return new_url
    else:
        print("Could not find year pattern in URL")
        return url

def try_alternative_pdf_urls(base_url, year):
    """
    Try different URL patterns for the PDF in case the main one fails.
    
    Args:
        base_url (str): Base URL pattern to try variations of
        year (int): Year to use in the URL
    
    Returns:
        list: List of alternative URLs to try
    """
    # Parse the base URL
    parsed_url = urlparse(base_url)
    base_path = parsed_url.path
    
    # Different patterns that might work
    patterns = [
        f"/{year}_QS_A4.pdf"
    ]
    
    # Create alternative URLs
    alternatives = []
    for pattern in patterns:
        # Replace the path in the URL
        new_path = os.path.dirname(base_path) + pattern
        
        alt_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            new_path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))
        
        alternatives.append(alt_url)
    
    return alternatives

def process_pdf_and_increment(start_url, start_year, end_year, output_dir="downloads"):
    """
    Process PDFs from start_year to end_year, extracting text and running final.py on each.
    
    Args:
        start_url (str): Initial URL to download
        start_year (int): Starting year
        end_year (int): Ending year
        output_dir (str): Directory to save downloaded PDFs
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the current script directory to properly locate final.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    final_script_path = os.path.join(script_dir, "final.py")
    
    current_url = start_url
    
    for year in range(start_year, end_year + 1):
        # Extract year from URL for filename
        filename = f"{year}_QS_M.pdf"  # Default filename pattern
        pdf_path = os.path.join(output_dir, filename)
        
        print(f"Processing year {year}...")
        
        # Try to download the PDF
        success = download_pdf(current_url, pdf_path)
        
        # If download failed, try alternative URL patterns
        if not success:
            print(f"Failed to download using the primary URL pattern for year {year}")
            alt_urls = try_alternative_pdf_urls(start_url, year)
            
            for alt_url in alt_urls:
                print(f"Trying alternative URL: {alt_url}")
                success = download_pdf(alt_url, pdf_path)
                if success:
                    current_url = alt_url  # Update the URL pattern if successful
                    break
        
        # Process the PDF if available
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            # Extract text from the PDF
            pdf_text = extract_text_from_pdf(pdf_path)
            
            if pdf_text:
                # Run final.py with the extracted text
                try:
                    print(f"Processing {filename} with final.py...")
                    # Fixed: Don't encode the text since subprocess.run will handle the encoding
                    result = subprocess.run(
                        [sys.executable, final_script_path],
                        input=pdf_text,  # Pass text directly, subprocess.run will handle encoding
                        capture_output=True,
                        text=True  # This tells subprocess to handle text encoding/decoding
                    )
                    print(f"Processed {filename} with final.py")
                    print(f"Output: {result.stdout}")
                    if result.stderr:
                        print(f"Errors: {result.stderr}")
                except Exception as e:
                    print(f"Error running final.py on {filename}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"No text extracted from {filename}")
        else:
            print(f"Could not process year {year}, no valid PDF available")
        
        # Increment the URL for the next iteration
        current_url = increment_year_in_url(current_url)

if __name__ == "__main__":
    # Starting URL - try various patterns for better success
    initial_url = "https://assets.wimbledon.com/archive/draws/pdfs/draws/2002_QS_M.pdf"
    
    # Process PDFs from 2002 to 2023 (adjust range as needed)
    process_pdf_and_increment(initial_url, 2002, 2003, output_dir="downloads")
