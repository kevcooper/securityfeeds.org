(() => {
    let drawTable = (feeds) => {
        let feedsTable = document.createElement("table", { id: "app-table" })
        feedsTable.id = "app-table"

        let labels = ["url", "title", "description", "type"]
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

            for (key in feed) {
                var td = document.createElement("td")
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
            }

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

        fetch("./feeds.json")
            .then(x => x.json())
            .then(ndata => {
                feeds = ndata
                drawTable(ndata.sort((a, b) => a.url > b.url))
            })

        app.onkeyup = (e) => {
            let searchTerm = document.getElementById("search-box").value
            let drawData = feeds.filter(x => JSON.stringify(x).toLowerCase().includes(searchTerm.toLowerCase()))
            document.getElementById("app-table").remove()
            drawTable(drawData)
        }

        app.appendChild(searchBoxDiv)
        document.body.appendChild(app)
    }

    if (document.addEventListener) {
        document.addEventListener('DOMContentLoaded', autorun, false)
    } else {
        window.onload = autorun
    }
})();