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

        }

        setup() {
            let jqueryObj = this.jqueryObj;
            let id = this.id;

            let remove = function(){
                jqueryObj.remove();
                delete sandboxes[id];
            };

            let stop = function(){
                let XHR = new XMLHttpRequest();
                XHR.open("DELETE", "/api/sandboxes/" + id, true);
                XHR.send();
            };

            this.trashBtn.on('click', remove);
            this.stopBtn.on('click', stop);
        }

        static fromTemplate(id){
            let card = $("<div></div>");
            card.html(cardHtmlTemplate
                .replace(/collapse-0/g, "collapse-" + id)
                .replace(/heading-0/g, "heading-"+id)
                .replace(/Sandbox 1/, "Sandbox " + (id + 1)));
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
            XHR.send(sandboxObjectList[i]);

        }
    });

    (function main(){
        sandboxes[0] = new SandboxCard(0, firstCard);
    })();

})();
