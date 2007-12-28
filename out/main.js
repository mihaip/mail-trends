// $ is used as a variable prefix in Cheetah, and we want to avoid conflicts 
// with embedded scripts
var _ = jQuery.noConflict();

function toggleStatCollectionSelection(selectNode) {
  var selectedStatId = _(selectNode).val();
  
  _("option", selectNode).each(function(i) {
    var statId = this.value;
    
    if (statId == selectedStatId) {
      _("#" + statId).removeClass("hidden");
    } else {
      _("#" + statId).addClass("hidden");        
    }
  });
}

function toggleTableStatTop(selectNode) {
  var top = _(selectNode).val();
  var statNode = selectNode.parentNode;
  
  while (!_(statNode).hasClass("stat")) {
    statNode = statNode.parentNode;
  }
  
  var tableNode = _("table.table-stat", statNode).get(0);
  
  _(tableNode).removeClass("top10");
  _(tableNode).removeClass("top20");
  _(tableNode).removeClass("top40");
  _(tableNode).addClass(top);
}