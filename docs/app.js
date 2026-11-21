(() => {
    // Decide how one mirrors.json entry is shown.
    //   ok      -> "mirror" link
    //   stale   -> "mirror (stale)" link: the last good copy is served, the latest fetch failed
    //   missing -> "unavailable", no link
    // Older workers say status "error" for both stale and missing; a previous
    // good fetch (last_ok) is what tells them apart.
    let mirrorState = (m) => {
        let status = String(m.status || "").toLowerCase()
        let state
        if (status === "ok") state = "ok"
        else if (status === "stale" || (status === "error" && m.last_ok)) state = "stale"
        else state = "missing"
        // Only link http(s) or same-site paths; anything else counts as missing.
        let href = String(m.mirror || "")
        if (!/^(https?:\/\/|\/(?!\/))/i.test(href)) { href = ""; state = "missing" }

        let notes = []
        if (state === "missing") notes.push(m.known_issue || m.error || "not mirrored yet")
        else {
            if (m.known_issue) notes.push(m.known_issue)
            if (state === "stale" && m.error) notes.push(`latest fetch failed: ${m.error}`)
            if (m.last_ok) notes.push(`last fetched ${m.last_ok}`)
            if (m.served_by) notes.push(`served by ${m.served_by}`)
        }
        return { state, href, title: notes.join("\n") }
    }

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
                        let { state, href, title } = mirrorState(feed.mirror)
                        td.classList.add(`mirror-${state}`)
                        td.title = title
                        if (state === "missing") {
                            td.textContent = "unavailable"
                        } else {
                            let a = document.createElement("a")
                            a.href = href
                            a.textContent = state === "stale" ? "mirror (stale)" : "mirror"
                            td.appendChild(a)
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
                let entries = (mdata && Array.isArray(mdata.feeds)) ? mdata.feeds : []
                let bySource = new Map(entries.filter(m => m && m.source).map(m => [m.source, m]))
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