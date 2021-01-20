// Add to menu without reload
$(document).ready(function() {
    $('.updateButton').on('click', function(){
        let recipe_id = $(this).attr('r_id')
        req = $.ajax({
            url : '/recipes/change_menu',
            type: 'POST',
            data: {recipe_id: recipe_id}
            });
        if (this.classList.contains("btn-success")){
            $(this).removeClass("btn-success").addClass("btn-light");
        } else{
            $(this).removeClass("btn-light").addClass("btn-success");
        }
    });
});

// Borrow without reload
$(document).ready(function() {
    $('.borrowButton').on('click', function(){
        let recipe_id = $(this).attr('r_id')
        req = $.ajax({
            url : '/recipes/change_borrow',
            type: 'POST',
            data: {recipe_id: recipe_id}
            });
        if (this.classList.contains("btn-info")){
            $(this).removeClass("btn-info").addClass("btn-light");
        } else{
            $(this).removeClass("btn-light").addClass("btn-info");
        }
    });
});

// Change to eaten without reload
$(document).ready(function() {
    $('.eatenButton').on('click', function(){
        let recipe_id = $(this).attr('e_id')
        let div = document.getElementById(recipe_id)
        let button = div.getElementsByTagName('BUTTON')[0]
        req = $.ajax({
            url : '/home/change_eaten',
            type: 'POST',
            data: {recipe_id: recipe_id}
            });
        if (button.classList.contains("btn-success")){
        $(button).removeClass("btn-success").addClass("btn-secondary");
        } else{
        $(button).removeClass("btn-secondary").addClass("btn-success");
        }
        // part that checks if all menu items are eaten, allows clear
        // let buttons = document.getElementsByClassName('menuItems');
        // let counter = 0
        // for (var buttonKey in button) {
        //     if (buttonKey.eaten){
        //         counter++
        //     }
        // }
        // if (counter==buttons.length){
        //     let clear = document.getElementsByClassName('clearButton')
        //     clear.value = 'true'
        // }
    });
});

// Strike-through on grocery-list items // todo not working
$(document).ready(function() {
    $('.groceries').on("click", function(){
    // let strike = $(this).attr('strike')
    let item_id = $(this).attr('itemid')
    $(this).css("text-decoration-color","text-muted");  // Not sure what this is doing

    if($(this).closest("s").length) {  // If there is an s =>1 else s=>0 ///Not sure what .closest does
        $(this).removeClass('text-muted')
        Content = $(this).parent("s").html();  // Why user .parent?
        $curParent = $(this).closest("s");
        $(Content).insertAfter($curParent);
        $(this).closest("s").remove();
        strike = 0
    }
    else {
        $(this).addClass('text-muted')
        $(this).wrapAll("<s />");
        strike = 1
    }
    req = $.ajax({
        url : '/home/change_grocerylist',
        type: 'POST',
        data: {strike: strike, item_id:item_id}
        });
    });
});

// Change menu button color and remove from menu in landing page
$(document).ready(function() {
    $('.menuButton').on('click', function() {
        if (this.classList.contains("btn-success")) {
            $(this).removeClass("btn-success").addClass("btn-light");
            this.value = "false";
        } else {
            $(this).removeClass("btn-light").addClass("btn-success");
            this.value = "true";
        }
        let menuItems = document.getElementsByClassName('card');
        for(let i = 0; menuItems.length; i++){
            if(menuItems[i].id === "0"){
                emptyItem = menuItems[i];
            }
            if(menuItems[i].id === this.id){
                menuItem = menuItems[i];
                break;
            }
        }
        if(this.value === 'true'){
            $(menuItem).fadeIn(0);
        } else {
            $(menuItem).fadeOut(0);
        }
        let hidden = 0
        for(x of menuItems){
            if(x.style.display === "none"){
                hidden++;
            }
        }
        if(hidden === 4){
            $(emptyItem).fadeIn(0);
        } else{
            $(emptyItem).fadeOut(0);
        }
    });
});

// Trying to add recommended recipe without reload
//var li = document.getElementsByTagName("li");
//
//for(var i = 0;i<li.length;i++){
//    li[i].addEventListener("click", myScript);
//}
//
//function myScript(e){
//    console.log(e.target.attributes.id.value);
//}
//document.getElementById("updateItems").addEventListener("click",function(e) {
//        // e.target is our targetted element.
//                    // try doing console.log(e.target.nodeName), it will result LI
//        console.log(e.target.id)
//        if(e.target == "LI") {
//        console.log(e.target.id)
//        let recipe_id = e.target.id
//            req = $.ajax({
//            url : '/recipes/add_menu',
//            type: 'POST',
//            data: {recipe_id: recipe_id}
//            });
//        }
//    });
//    $('.updateItem').on('click', function(){
//        let recipe_id = $(this).attr('r_id')
//
//        req = $.ajax({
//            url : '/recipes/add_menu',
//            type: 'POST',
//            data: {recipe_id: recipe_id}
//            });
//        if (this.classList.contains("btn-success")){
//        $(this).removeClass("btn-success").addClass("btn-light");
//        } else{
//        $(this).removeClass("btn-light").addClass("btn-success");
//        }
//    });
//});

