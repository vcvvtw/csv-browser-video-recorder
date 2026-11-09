import csv
import os
import qscript

qscript.PATH_TO_VIDEO_FOLDER = "./video"
CSV_FILE_PATH = "input.csv"


def get_field(row, *possible_keys, default=""):
    """Fetch field value with fallback for whitespace variations in headers."""
    for key in possible_keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
        for actual_k, v in row.items():
            if actual_k and actual_k.strip() == key.strip() and v is not None:
                return str(v).strip()
    return default


def main():
    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        return

    with open(CSV_FILE_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        for row in reader:
            url = get_field(row, "URL")
            company_name = get_field(row, "Company Name")
            language = get_field(row, "Language")
            country = get_field(row, "Country")
            postcode = get_field(row, "Postcode")
            city = get_field(row, "City")
            street = get_field(row, "Street")
            house_no = get_field(row, "HouseNo")

            video_path = qscript.CaptureVideo_Magento(
                url=url,
                company_name=company_name,
                language=language,
                country=country,
                postcode=postcode,
                city=city,
                street=street,
                house_no=house_no,
            )
            print(video_path)


if __name__ == "__main__":
    main()
