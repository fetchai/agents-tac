  (function() {

    let firstCard = $("#card-0");
    let cardHtmlTemplate = firstCard.html();
    let sandboxes = {};
    let accordion = $("#accordion");

    class SandboxCard {

        constructor(id, jqueryObj){
            this.id = id;
            this.jqueryObj = jqueryObj;
            this.trashBtn = this.jqueryObj.find("button[name='btn-remove-item']");
            this.stopBtn = this.jqueryObj.find("button[name='btn-stop-item']");

            this.setup();

            //this.getSandboxStatus()

        }

        setup() {
            let jqueryObj = this.jqueryObj;
            let id = this.id;

            let process_statusBtn = document.getElementById("process-status-sandbox-"+ id);
            let controller_statusBtn = document.getElementById("controller-status-sandbox-" + id);
            let game_id = document.getElementById("info-game-id-" + id);


            let remove = function(){
                jqueryObj.remove();
                delete sandboxes[id];
            };

            let stop = function(){
                let XHR = new XMLHttpRequest();
                XHR.open("DELETE", "/api/sandboxes/" + id, true);
                XHR.send();
            };

            let  getSandboxStatus = function() {
                let XHR = new XMLHttpRequest();
                XHR.onreadystatechange = function () {
                    if (this.readyState == 4 && this.status == 200) {
                        if (XHR.response != null && XHR.response != "null" && XHR.response != ""){
                            let jsonResponse = JSON.parse(XHR.response);

                            document.getElementById("process-status-sandbox-"+ id).innerHTML = "Process Status: " + jsonResponse["process_status"];
                            document.getElementById("controller-status-sandbox-" + id).innerHTML = "Controller Status: " + jsonResponse["controller_status"];
                            document.getElementById("info-game-id-" + id).innerHTML = "Game Id: " +  jsonResponse["game_id"]

                        }
                    }
                };
                XHR.open("GET", "/api/sandboxes/" + id, true);
                XHR.send();
                setTimeout(getSandboxStatus, 500);
            }
            getSandboxStatus()

            this.trashBtn.on('click', remove);
            this.stopBtn.on('click', stop);


        }

        static fromTemplate(id){
            let card = $("<div></div>");
            card.html(cardHtmlTemplate
                .replace(/collapse-0/g, "collapse-" + id)
                .replace(/heading-0/g, "heading-"+id)
                .replace(/Sandbox 1/, "Sandbox " + (id + 1))
                .replace('process-status-sandbox-0', "process-status-sandbox-"+id)
                .replace('controller-status-sandbox-0', "controller-status-sandbox-"+id)
                .replace('info-game-id-0', "info-game-id-"+id));
            card.addClass("card");
            card.attr("id", "card-" + id);

            accordion.append(card);
            let jqueryObj = $('#card-'+id);
            return new SandboxCard(id, jqueryObj);
        }



    }

    function buildJSONFromSandboxFormList(){
        let result = [];
        for (let sandboxId in sandboxes){
            let inputs = sandboxes[sandboxId].jqueryObj.find('.card-body :input');
            let values = {};
            inputs.each(function() {
                values[this.name] = $(this).val();
            });
            result.push(values);
        }
        return result
    }

    $("#btn-add-sandbox").on("click", function(){
        let nbCards = Object.keys(sandboxes).length;
        let card = SandboxCard.fromTemplate(nbCards);
        sandboxes[card.id] = card;
    });

    $("#btn-submit-gridsearch").on("click", function() {
        let sandboxObjectList = buildJSONFromSandboxFormList();
        for (let i = 0; i < sandboxObjectList.length; i++) {
            console.log("POST /api/sandboxes for Sandbox " + i);
            let XHR = new XMLHttpRequest();
            XHR.addEventListener("error", function (event) {
                console.log("Error on request " + i + " event: " + event)
            });
            XHR.open("POST", "/api/sandboxes", true);
                        // Display the key/value pairs
            console.log("Form data");
            let FD = sandboxObjectList[i];
            for (var pair in FD) {
                console.log(pair);
            }
            XHR.send(FD);

        }
    });

    (function main(){
        sandboxes[0] = new SandboxCard(0, firstCard);
    })();

})();
