## Setup and Running the Application

Follow these steps to get the application up and running on your local machine.

### Prerequisites
* Python 3.8+
* Git
* **Tesseract OCR Engine:** You must install the Tesseract OCR engine on your system.
    * **Windows:** Download installer from [Tesseract-OCR GitHub](https://github.com/UB-Mannheim/tesseract/wiki). Add to PATH during installation.
    * **macOS:** `brew install tesseract` and `brew install tesseract-lang`
    * **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install tesseract-ocr libtesseract-dev`

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/receipt-analyzer-assignment.git](https://github.com/YOUR_USERNAME/receipt-analyzer-assignment.git)
    cd receipt-analyzer-assignment
    ```
    (Replace `YOUR_USERNAME` with your GitHub username)

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

You will need two separate terminal windows for the backend and frontend. **Ensure both terminals are in the `receipt_analyzer` root directory.**

1.  **Start the Backend (FastAPI):**
    Open the first terminal, activate the virtual environment, and run:
    ```bash
    uvicorn backend.main:app --reload
    ```
    The backend API will be accessible at `http://127.0.0.1:8000`.

2.  **Start the Frontend (Streamlit):**
    Open the second terminal, activate the virtual environment, and run:
    ```bash
    streamlit run frontend/app.py
    ```
    The Streamlit application will open in your web browser (usually at `http://localhost:8501`).

## Design Choices / Architecture / Journeys

### Architecture Overview
The application follows a client-server architecture:
* **Frontend (Streamlit):** Serves as the user interface, handling user interactions (file uploads, data display, editing). It communicates with the backend via HTTP requests.
* **Backend (FastAPI):** Acts as the API layer, responsible for:
    * Receiving uploaded files.
    * Performing OCR and data parsing.
    * Storing and retrieving data from the database.
    * Implementing core algorithms (search, sort, aggregation).
    * Serving static uploaded files.
* **Database (SQLite):** A lightweight, file-based relational database used for persistent storage of extracted receipt data.

### Data Flow / User Journey
1.  **User Uploads File:** User navigates to the "Upload & View" page in Streamlit and uploads a receipt/bill file.
2.  **Frontend to Backend:** Streamlit sends the file to the FastAPI `/upload-receipt/` endpoint.
3.  **Backend Processing:**
    * FastAPI saves the file to the `backend/uploads/` directory.
    * It determines the file type and uses `pytesseract` for OCR on images/PDFs (or reads text directly from `.txt`).
    * The `parser.py` module applies rule-based regular expressions to extract `vendor`, `date`, `amount`, and `category` from the OCR text.
    * Pydantic models (`ReceiptCreate`) validate the extracted data.
    * The validated data is stored in the SQLite database via SQLAlchemy.
4.  **Backend Response:** FastAPI sends back the newly created receipt's details (including its generated ID).
5.  **Frontend Display:** Streamlit updates the "All Uploaded Receipts" table with the new entry.
6.  **User Views Insights:** User navigates to the "Insights & Analytics" page.
7.  **Frontend Requests Insights:** Streamlit calls the FastAPI `/insights/` endpoint.
8.  **Backend Aggregation:** The `algorithms.py` module performs various aggregations (sum, mean, median, mode, frequency distributions, time-series trends) on all stored receipts.
9.  **Backend Response:** FastAPI returns the aggregated data.
10. **Frontend Visualization:** Streamlit uses Pandas, Matplotlib, and Seaborn to render interactive charts and metrics based on the received insights.
11. **Manual Correction:** On the "Upload & View" page, users can select a receipt, modify its parsed fields, and send an `UPDATE` request to the backend.

### Algorithmic Choices
* **OCR & Parsing:** `pytesseract` is chosen for its simplicity and effectiveness for basic OCR. Rule-based regex parsing is used for its directness in extracting specific fields, suitable for a mini-application. For production, more advanced NLP/ML models would be required.
* **Search:** Linear search is implemented for simplicity. For larger datasets, database indexing (already applied in `database.py`) combined with database-native search capabilities would be more efficient. Hashed indexing for specific fields could be added for very fast exact lookups.
* **Sorting:** Python's built-in `sorted()` function, which uses Timsort, is highly optimized and efficient ($O(n \log n)$ average/worst case), making it suitable for in-memory sorting.
* **Aggregation:** Native Python data structures (`list`, `dict`, `collections.Counter`) are used for efficient in-memory computation of statistical aggregates.

## Limitations and Assumptions

### Limitations
* **OCR Accuracy:** The OCR and rule-based parsing are highly dependent on the quality and format of the input receipts. Complex layouts, poor image quality, or unusual fonts will significantly reduce accuracy.
* **PDF Support:** Current PDF handling is minimal (only stores filename and placeholder text). Full PDF text extraction or image conversion for OCR is not implemented.
* **Currency Detection:** The application does not automatically detect currency. Amounts are treated as generic floats.
* **Multi-Language Support:** OCR is configured for English (`lang='eng'`). Multi-language receipts are not explicitly supported.
* **Advanced NLP:** No advanced Natural Language Processing (NLP) or Machine Learning models are used for parsing, categorisation, or anomaly detection.
* **Scalability:** SQLite is suitable for a mini-application. For large-scale deployments, a more robust database system (e.g., PostgreSQL) would be necessary.
* **Error Handling:** While basic exception handling is in place, more granular error messages and user feedback could be implemented.
* **User Authentication:** No user authentication or authorization is implemented. All data is accessible globally within the application.

### Assumptions
* **Tesseract Installation:** It is assumed that the Tesseract OCR engine is correctly installed and configured on the system where the backend is run.
* **Receipt Format:** Assumes a relatively structured format for receipts where vendor names, dates, and total amounts can be identified using common patterns.
* **Single File Upload:** The application handles one file upload at a time.
* **Local Deployment:** The application is designed for local deployment, with the frontend and backend running on the same machine (or accessible over a local network).
* **Positive Amounts:** The application assumes that all valid receipt amounts will be greater than zero.
* **Timezone:** Dates are handled as naive `datetime` objects. For a production system, explicit timezone handling would be crucial.

## (Optional) Video Demonstration
A 2-3 minute video or screen recording demonstrating the project's key functionalities (uploading, viewing, editing, insights) would be a great addition. You can use tools like OBS Studio, Loom, or your operating system's built-in screen recorder.

---
