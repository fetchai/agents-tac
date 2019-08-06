(function() {

    let card_html_template = $("#card-1").html();
    let sandboxList = $("#accordion");

    let createSandboxCard = function(id){
        let card = $("<div></div>");
        card.html(card_html_template
            .replace(/collapse-1/g, "collapse-" + id)
            .replace(/heading-1/g, "heading-"+id)
            .replace(/Sandbox 1/, "Sandbox " + id));
        card.addClass("card");
        card.attr("id", "card-" + id);
        return card;
    };

    $("#btn-add-sandbox").on("click", function(){
        let card = createSandboxCard(sandboxList.children().length + 1);
        sandboxList.append(card);
    });




})();
