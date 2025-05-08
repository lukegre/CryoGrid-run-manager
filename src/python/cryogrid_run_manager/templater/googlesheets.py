from typing import Union


def _get_sheet_id_from_url(url: str) -> str:
    """
    Extracts the sheet ID from a Google Sheets URL.

    Args:
        url (str): The URL of the Google Sheets document.

    Returns:
        str: The extracted sheet ID.
    """
    # Check if the URL is in the expected format
    if "docs.google.com/spreadsheets/d/" not in url:
        raise ValueError("Invalid Google Sheets URL.")

    # Split the URL and extract the sheet ID
    parts = url.split("/")
    sheet_id = parts[5]

    return sheet_id


def make_downloadable_url(sheet_url: str) -> str:
    """
    Constructs a downloadable URL for a specific sheet in a Google Sheets document.

    Args:
        sheet_url (str): The URL of the Google Sheets document.
        sheet_name [int / str]: The name or index of the specific sheet to download.
        filetype (str): The type of file to download. Excel=xlsx, CSV=csv, TSV=tsv. Defaults to 'csv'.

    Returns:
        str: The constructed downloadable URL.
    """

    # Extract the sheet ID from the URL
    sheet_id = _get_sheet_id_from_url(sheet_url)

    # Construct the URL for downloading the sheet
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

    return url


def download_google_sheet_as_excel(
    sheet_url: str, dest_fpath: str, overwrite: bool = False
) -> str:
    """
    Opens a Google Sheets document and returns its content as a string.

    Args:
        sheet_url (str): The URL of the Google Sheets document.
        sheet_name (str): The name of the specific sheet to open.

    Returns:
        str: The content of the Google Sheets document.
    """
    import pathlib

    import pooch

    # Construct the downloadable URL
    url = make_downloadable_url(sheet_url)

    path = pathlib.Path(dest_fpath)

    if overwrite and path.exists():
        # Remove the file if it already exists
        path.unlink()

    # Download the file with pooch
    filename = pooch.retrieve(
        url,
        None,
        fname=path.name,
        path=str(path.parent),
        progressbar=True,
    )

    return filename
