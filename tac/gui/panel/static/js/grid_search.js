(function() {

    let firstCard = $("#card-0");
    let cardHtmlTemplate = firstCard.html();
    firstCard.find("button[name='btn-remove-item']").on('click', function(){
        firstCard.remove();
    });

    let sandboxList = $("#accordion");
    let nbCards = 1;

    let createSandboxCard = function(id){
        let card = $("<div></div>");
        card.html(cardHtmlTemplate
            .replace(/collapse-0/g, "collapse-" + id)
            .replace(/heading-0/g, "heading-"+id)
            .replace(/Sandbox 1/, "Sandbox " + (id + 1)));
        card.addClass("card");
        card.attr("id", "card-" + id);

        //remove card function
        card.find("button[name='btn-remove-item']").on('click', function(){
            card.remove();
        });
        return card;
    };

    let buildJSONFromSandboxFormList = function(){
        let result = [];
        let nbCards = sandboxList.children().length;
        for (let i = 0; i < nbCards; i++){
            let inputs = $('#card-' + i).find('.card-body :input');
            let values = {};
            inputs.each(function() {
                values[this.name] = $(this).val();
            });
            result.push(values);
        }
        return result
    };

    $("#btn-add-sandbox").on("click", function(){
        let card = createSandboxCard(nbCards);
        sandboxList.append(card);
        nbCards += 1;
    });

    $("#btn-submit-gridsearch").on("click", function(){
        let sandboxObjectList = buildJSONFromSandboxFormList();
        console.log(sandboxObjectList)
    });




})();
