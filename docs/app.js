(() => {
    let drawTable = (feeds) => {
        let feedsTable = document.createElement("table", { id: "app-table" })
        feedsTable.id = "app-table"

        let labels = ["url", "mirror", "title", "description", "type"]
        let labelrow = document.createElement("tr")

        labels.forEach((label) => {
            var th = document.createElement("th")
            th.innerHTML = label
            labelrow.appendChild(th)
        })

        feedsTable.appendChild(labelrow)

        let app = document.getElementById("app")

        feeds.forEach(feed => {
            var tr = document.createElement("tr")

            labels.forEach((key) => {
                var td = document.createElement("td")
                if (key === "mirror") {
                    // Cached copy served by securityfeeds.org/mirror (see mirrors.json).
                    td.className = "mirror"
                    if (feed.mirror) {
                        let a = document.createElement("a")
                        a.href = feed.mirror.url
                        a.textContent = "mirror"
                        td.appendChild(a)
                        if (feed.mirror.known_issue) {
                            td.appendChild(document.createTextNode(" (unavailable)"))
                            td.title = feed.mirror.known_issue
                        }
                    }
                    tr.appendChild(td)
                    return
                }
                if (key === "tagss") {
                    var arr = [...feed[key]].map(x => `#${x}`)
                    var text = arr.join(",")
                } else if (key === "description" && feed[key] != null) {
                    var text = feed[key].substring(0,100)
                } else {
                    var text = feed[key]
                }

                // if (text === "" || text === null) {
                //     continue
                // }
                td.innerHTML = text
                tr.appendChild(td)
            })

            feedsTable.appendChild(tr)
        })

        app.appendChild(feedsTable)
    }

    let autorun = () => {
        let app = document.createElement("div")
        app.id = "app"

        let searchBox = document.createElement("input", { type: "text" })
        searchBox.id = "search-box"

        let searchBoxDiv = document.createElement("div")
        searchBoxDiv.classList += "search"
        searchBoxDiv.innerHTML = "search: "
        searchBoxDiv.appendChild(searchBox)

        var data = null
        var feeds = null

        // Mirror links are optional: if /mirror/mirrors.json can't be loaded,
        // the table renders exactly as before, just with an empty mirror column.
        let mirrors = fetch("/mirror/mirrors.json")
            .then(x => x.ok ? x.json() : { feeds: [] })
            .catch(() => ({ feeds: [] }))

        Promise.all([fetch("./feeds.json").then(x => x.json()), mirrors])
            .then(([ndata, mdata]) => {
                let bySource = new Map((mdata.feeds || []).map(m => [m.source, { url: m.mirror, known_issue: m.known_issue }]))
                ndata.forEach(feed => {
                    let m = bySource.get(feed.url)
                    if (m) feed.mirror = m
                })
                feeds = ndata
                drawTable(ndata.sort((a, b) => a.url > b.url))
            })

        app.onkeyup = (e) => {
            let searchTerm = document.getElementById("search-box").value
            let drawData = feeds.filter(x => JSON.stringify({ ...x, mirror: undefined }).toLowerCase().includes(searchTerm.toLowerCase()))
            document.getElementById("app-table").remove()
            drawTable(drawData)
        }

        app.appendChild(searchBoxDiv)
        document.body.appendChild(app)
        document.getElementById("search-box").focus()
    }

    if (document.addEventListener) {
        document.addEventListener('DOMContentLoaded', autorun, false)
    } else {
        window.onload = autorun
    }
})();