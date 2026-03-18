import sqlite3
import requests

# SQLite setup
DB_PATH = "data/citation_analyzer.db"


def get_db_metrics(author_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Total Citations count in db
    cursor.execute("SELECT COUNT(*) FROM citations WHERE target_id = ?", (author_id,))
    total_db = cursor.fetchone()[0]

    # 2. Notable citations
    cursor.execute(
        "SELECT COUNT(*) FROM citations WHERE target_id = ? AND notable_authors != '[]' AND notable_authors IS NOT NULL",
        (author_id,),
    )
    notable_db = cursor.fetchone()[0]

    # 3. Seminal citations
    cursor.execute(
        "SELECT COUNT(*) FROM citations WHERE target_id = ? AND is_seminal = 1",
        (author_id,),
    )
    seminal_db = cursor.fetchone()[0]

    conn.close()
    return total_db, notable_db, seminal_db


def get_api_metrics(author_id):
    url = f"http://localhost:3000/api/citations?target_id={author_id}"
    try:
        # Add session cookie for authentication (required for private groups like Wenzheng Chen)
        cookies = {"session_token": "super_admin_test_token"}
        response = requests.get(url, cookies=cookies)
        data = response.json()

        records = data.get("records", [])

        total_api = len(records)
        notable_api = sum(
            1
            for r in records
            if r.get("notable_authors") and len(r.get("notable_authors")) > 0
        )
        seminal_api = sum(1 for r in records if r.get("is_seminal"))

        return total_api, notable_api, seminal_api
    except Exception as e:
        print(f"API Error: {e}")
        return None, None, None


def validate(author_id, name):
    print(f"\nEvaluating: {name} ({author_id})")

    total_db, notable_db, seminal_db = get_db_metrics(author_id)
    total_api, notable_api, seminal_api = get_api_metrics(author_id)

    print("Database Metrics:")
    print(f"Total: {total_db}, Notable: {notable_db}, Seminal: {seminal_db}")

    print("\nAPI Metrics:")
    print(f"Total: {total_api}, Notable: {notable_api}, Seminal: {seminal_api}")

    if (
        total_db == total_api
        and notable_db == notable_api
        and seminal_db == seminal_api
    ):
        print("\n✅ CROSS VALIDATION PASSED!")
    else:
        print("\n❌ CROSS VALIDATION FAILED!")


if __name__ == "__main__":
    # Task 1: Yangyan Li
    validate("9RxI7UAAAAAJ", "Yangyan Li")
    # Task 2: Wenzheng Chen
    validate("KzhR_TsAAAAJ", "Wenzheng Chen")
    # Task 3: Jinming Cao
    validate("GSte8PMAAAAJ", "Jinming Cao")
