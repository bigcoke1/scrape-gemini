"use strict";

(function () {
    window.addEventListener("load", init);

    const URL = "https://www.scrape-insight.com"
    const MONTH = 2592000000;

    async function init() {
        qs("#register form").addEventListener("submit", makeRegisterRequest);
        qs("#login form").addEventListener("submit", makeLoginRequest);
        qs("#login > button").addEventListener("click", displayRegister);
        qs("#register > button").addEventListener("click", displayLogin);
        qs("#textbox input").addEventListener("change", toggleSubmit);
        id("textbox").addEventListener("submit", makeRequest);
        id("signout-btn").addEventListener("click", signOut);
        id("clear-btn").addEventListener("click", clearHistory);
        id("account-btn").addEventListener("click", displayAccount);
        id("home-btn").addEventListener("click", displayHome);

        await checkCookie();
    }
    
    async function displayAccount() {
        id("home").classList.add("hidden");
        id("login").classList.add("hidden");
        id("register").classList.add("hidden");
        id("account").classList.remove("hidden");

        let accountInfo = qsa("#account p");
        accountInfo[0].textContent = "Username: " + getCookie("username");
        let email = await makeAccountRequest(getCookie("username"));
        accountInfo[1].textContent = "Email: " + email;

    }

    async function makeAccountRequest(username) {
        let res = await fetch(URL + "/account/" + username);
        await statusCheck(res);
        res = await res.text();
        return res;
    }

    function setCookie(name, value, options = {}) {
        let cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;
    
        if (options.expires) {
            cookie += `; expires=${options.expires}`;
        }
        if (options.path) {
            cookie += `; path=${options.path}`;
        }
        if (options.domain) {
            cookie += `; domain=${options.domain}`;
        }
        if (options.secure) {
            cookie += `; secure`;
        }
        if (options.sameSite) {
            cookie += `; SameSite=${options.sameSite}`;
        }
    
        document.cookie = cookie;
    }

    function getCookie(name) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            let [cookieName, cookieValue] = cookie.split('=').map(c => c.trim());
            if (cookieName === encodeURIComponent(name)) {
                return decodeURIComponent(cookieValue);
            }
        }
        return null;
    }

    function deleteCookie(name) {
        document.cookie = `${encodeURIComponent(name)}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }

    async function clearHistory() {
        try {
            let params = new FormData();
            params.append("username", getCookie("username"));
            let res = await fetch(URL + "/clear", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            await makeChatRequest();
            id("chat").innerHTML = "";
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    async function checkCookie() {
        if (getCookie("username")) {
            await displayHome();
            if (getCookie("username") === "test") {
                let fileInput = document.createElement("input");
                fileInput.type = "file";
                fileInput.id = "file-input";
                id("textbox").appendChild(fileInput);
                fileInput.addEventListener("change", feedQuestions);
            }
        } else {
            displayLogin();
        }
    }

    function displayLogin() {
        id("home").classList.add("hidden");
        id("login").classList.remove("hidden");
        id("register").classList.add("hidden");
        id("account").classList.add("hidden");
    }

    async function signOut() {
        deleteCookie("username");
        await checkCookie();
    }

    function displayRegister() {
        id("home").classList.add("hidden");
        id("login").classList.add("hidden");
        id("register").classList.remove("hidden");
        id("account").classList.add("hidden");
    }

    async function displayHome() {
        id("home").classList.remove("hidden");
        id("login").classList.add("hidden");
        id("register").classList.add("hidden");
        id("chat").innerHTML = "";
        id("account").classList.add("hidden");

        await makeChatRequest();
    }

    async function makeChatRequest() {
        try {
            let username = getCookie("username");
            let res = await fetch(URL + "/get-all-chat/" + username);
            await statusCheck(res);
            res = await res.json();
            populateSidebar(res);
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    function populateSidebar(res) {
        id("sidebar").innerHTML = "";

        let data = {};
        
        for (let i = 0; i < res.length; i++) {
            let date = res[i][4];
            if (!data[date]) {
                data[date] = [];
            } 
            data[date].push(res[i]);
        }

        for (let date in data) {
            let dateTitle = document.createElement("h2");
            dateTitle.textContent = date;
            dateTitle.addEventListener("click", ()=> {
                populateChat(data[date]);
            });
            for (let i = 0; i < data[date].length; i++) {
                let queryTitle = document.createElement("h3");
                queryTitle.textContent = data[date][i][2];
                queryTitle.addEventListener("click", () => {
                    populateChat([data[date][i]]);
                });
                queryTitle.addEventListener("dblclick", async () => {
                    await deleteChat(data[date][i][0]);
                });
                id("sidebar").prepend(queryTitle);
            }
            id("sidebar").prepend(dateTitle);
        }
    }

    async function deleteChat(id) {
        try {
            let params = new FormData();
            params.append("id", id);
            let res = await fetch(URL + "/delete", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            await makeChatRequest();
        } catch (err) {
            handleError();
        }
    }
    function populateChat(res) {
        id("chat").innerHTML = "";
        for(let i = 0; i < res.length; i++) {
            let entry = res[i];
            displayEntry(entry[2], false);
            displayEntry(entry[3], true, JSON.parse(entry[5]), entry[2]);
        }
    }

    function setExpirationDate() {
        let expirationDate = new Date();
        expirationDate.setTime(expirationDate.getTime() + MONTH);

        let expires = expirationDate.toUTCString();

        return expires;
    }

    async function makeRegisterRequest(e) {
        try {
            e.preventDefault();
            let params = new FormData(qs("#register form"));
            let res = await fetch(URL + "/register", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            let username = qs("#register form input").value;
            setCookie("username", username, {expires: setExpirationDate()});
            await displayHome();
        } catch (err) {
            console.log(err);
            displayLoginError();
        }
    }

    async function makeLoginRequest(e) {
        try {
            e.preventDefault();
            let params = new FormData(qs("#login form"));
            let res = await fetch(URL + "/login", {
                method: "POST",
                body: params
            });
            await statusCheck(res);
            let username = qs("#login form input").value;
            setCookie("username", username, {expires: setExpirationDate()});
            await displayHome();
        } catch (err) {
            console.log(err);
            displayLoginError();
        }
    }

    function toggleSubmit() {
        let button = qs("#textbox button");
        if (this.value.replaceAll(" ", "")){
            button.disabled = false;
        } else {
            button.disabled = true;
        }
    }

    async function makeRequest(e) {
        try{
            e.preventDefault();
            let query = qs("#textbox input").value;
            displayEntry(query, false);
            await generateResponse();

            qs("#textbox button").disabled = false;
            qs("#textbox input").value = "";
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    async function generateResponse(query) {
        let loading = displayLoading();
        qs("#textbox button").disabled = true;
        let username = getCookie("username");
        let params = new FormData();
        params.append("query", query);
        params.append("username", username);
        let res = await fetch(URL + "/getresponse", {
            method: "POST",
            body: params
        });
        await statusCheck(res);
        res = await res.json();
        let aiResponse = res[0];
        let links = res[1];
        loading.remove();
        displayEntry(aiResponse, true, links, query);
        await makeChatRequest();
    }

    function displayLoading() {
        let resTextbox = document.createElement("article");
        let aiImage = document.createElement("img");
        aiImage.src = "static/images/AI.png";
        resTextbox.prepend(aiImage);

        let loadingImage = document.createElement("img");
        loadingImage.src = "static/images/loading.gif";
        resTextbox.appendChild(loadingImage);
        resTextbox.classList.add("chat-entry");
        resTextbox.classList.add("response");
        resTextbox.classList.add("shadow");

        id("chat").appendChild(resTextbox);
        id("chat").scrollTop = id("chat").scrollHeight;

        return resTextbox;
    }

    function displayEntry(res, response, links=null, query=null) {
        let resTextbox = document.createElement("article");
        let text = document.createElement("p");
        text.textContent = res;

        if (links) {
            // Create a text node for the initial text and the "References:" label
            text.appendChild(document.createTextNode("\nReferences: "));
            for (let i = 0; i < links.length; i++) {
                // Create a text node for the link index and description
                text.appendChild(document.createTextNode("\n" + (i + 1) + ") "));
        
                let urlElement = document.createElement("a");
                urlElement.href = links[i];
                urlElement.textContent = links[i];
                
                // Append the anchor element
                text.appendChild(urlElement);
            }
        }
        let subTextbox = document.createElement("section");
        subTextbox.appendChild(text);
        subTextbox.classList.add("sub-textbox")
        resTextbox.appendChild(subTextbox);
        resTextbox.classList.add("chat-entry");
        if (response) {
            resTextbox.classList.add("response");
            let img = document.createElement("img");
            img.src = "static/images/AI.png";
            resTextbox.prepend(img);
            let newAnswerButton = document.createElement("button");
            newAnswerButton.textContent = "Regenerate Response";
            newAnswerButton.addEventListener("click", () => {
                id("chat").appendChild(resTextbox.previousElementSibling);
                resTextbox.remove();
                generateResponse(query);
            });
            subTextbox.appendChild(newAnswerButton);
        } else {
            resTextbox.classList.add("question");
            let img = document.createElement("img");
            img.src = "static/images/user.png";
            resTextbox.appendChild(img);
        }
        resTextbox.classList.add("shadow");
        id("chat").appendChild(resTextbox);
    }

    async function feedQuestions(e) {
        try {
            e.preventDefault();
            let username = getCookie("username");
            let file = id("file-input").files[0];
            console.log(file);
            if (file) {
                let reader = new FileReader();
                reader.readAsText(file);
                reader.onload = function(e) {
                    console.log("inside");
                    let fileContent = e.target.result;
                    let lines = fileContent.split("\n");

                    lines.forEach(async (line, index) => {
                        let params = new FormData();
                        params.append("query", line);
                        params.append("username", username);
                        console.log(line);
                        let res = await fetch(URL + "/getresponse", {
                            method: "POST",
                            body: params
                        });
                        await statusCheck(res);
                    });
                }
            }
        } catch (err) {
            console.log(err);
            handleError();
        }
    }

    function handleError() {
        let error = document.createElement("p");
        error.textContent = "An Error Occured. Try Again Later!";
        error.classList.add("error");
        id("chat").appendChild(error);
    }

    function displayLoginError() {
        qs("#login p").classList.remove("hidden");
        qs("#register p").classList.remove("hidden");
        setTimeout(() => {
            qs("#login p").classList.add("hidden");
            qs("#register p").classList.add("hidden");
        }, 3000);
    }

    /**
     * Returns the element that has the ID attribute with the specified value.
     * @param {string} id - element ID.
     * @returns {object} - DOM object associated with id.
     */
    function id(id) {
        return document.getElementById(id);
    }

    /**
     * Returns first element matching selector.
     * @param {string} selector - CSS query selector.
     * @returns {object} - DOM object associated selector.
     */
    function qs(selector) {
        return document.querySelector(selector);
    }

    /**
     * Returns the array of elements that match the given CSS selector.
     * @param {string} query - CSS query selector
     * @returns {object[]} array of DOM objects matching the query.
     */
    function qsa(query) {
        return document.querySelectorAll(query);
    }

    /**
     * Helper function to return the response's result text if successful, otherwise
     * returns the rejected Promise result with an error status and corresponding text
     * @param {object} res - response to check for success/error
     * @return {object} - valid response if response was successful, otherwise rejected
     *                    Promise result
     */
    async function statusCheck(res) {
        if (!res.ok) {
        throw new Error(await res.text());
        }
        return res;
    }
})()