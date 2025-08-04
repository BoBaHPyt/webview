package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    "strings"

    "fyne.io/fyne/v2"
    "fyne.io/fyne/v2/app"
    "fyne.io/fyne/v2/container"
    "github.com/webview/webview"
)

const customUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

func handleCustomProtocol(u *url.URL) (string, map[string]string) {
    query := u.Query()
    cookieStr := query.Get("cookie")
    var cookies map[string]string
    json.Unmarshal([]byte(cookieStr), &cookies)
    return u.Host, cookies
}

func setCookies(wv webview.WebView, host string, cookies map[string]string) {
    for key, value := range cookies {
        wv.Dispatch(func() {
            wv.Eval(fmt.Sprintf(`document.cookie="%s=%s";`, key, value))
        })
    }
}

func main() {
    a := app.New()
    w := a.NewWindow("Custom WebView")

    // Инициализация WebView
    wv := webview.New(true)
    defer wv.Destroy()

    wv.SetSize(800, 600)
    wv.SetTitle("Custom WebView")
    wv.SetNavigationCallback(func(req string) bool {
        u, err := url.Parse(req)
        if err != nil {
            fmt.Println("Error parsing URL:", err)
            return false
        }

        if u.Scheme == "autotrader" {
            host, cookies := handleCustomProtocol(u)
            setCookies(wv, host, cookies)
            wv.Dispatch(func() {
                wv.Navigate(fmt.Sprintf("https://%s", host))
            })
            return false
        }

        return true
    })

    wv.Dispatch(func() {
        wv.SetUserAgent(customUserAgent)
        wv.Navigate("about:blank")
    })

    // Создание контейнера для WebView
    w.SetContent(container.NewWithoutLayout(fyne.NewContainerWithLayout(nil, fyne.NewWidgetFromCanvasObject(&wv))))
    w.ShowAndRun()
}
