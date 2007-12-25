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
