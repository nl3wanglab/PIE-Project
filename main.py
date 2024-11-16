import webview

def main():
    # Create a webview window
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700)
    webview.start()

if __name__ == "__main__":
    main() 