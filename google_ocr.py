from google.cloud import vision
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "c:\\Users\\ADMIN\\OneDrive\\Project-2025\\Insurance_ocr\\insurance-455717-585a82184303.json"



def detect_text(path):
    """Detects text in the file located in Google Cloud Storage or on the Web."""
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations

    print('Texts:')

    for text in texts:
        print('\n"{}"'.format(text.description))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: https://cloud.google.com/apis/design/errors'.format(
                response.error.message))

if __name__ == '__main__':
    # Replace 'path_to_image.jpg' with the path to the image file you want to analyze.
    detect_text('1.jpg')
