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

function toggleTabStat(idPrefix) {
  var title = _("#" + idPrefix + "-title");
  var titleNode = title.get(0);
  
  var tabNode = titleNode.parentNode;  
  while (!_(tabNode).hasClass("stat-tabs")) {
    tabNode = tabNode.parentNode;
  }
  
  _("li.stat-tab-title", tabNode).removeClass("selected");
  title.addClass("selected");
  
  _(".stat-tab-pane", tabNode).addClass("hidden");
  _("#" + idPrefix + "-pane").removeClass("hidden");
}

var SEARCH_PREFIX = "#search/";
var APPS_PREFIX = "https://mail.google.com/a/";
var GMAIL_PREFIX = "http://mail.google.com/mail/";

function runSearch(query) {
  window.open(
      (MAIL_HOST == "gmail.com" ? GMAIL_PREFIX : APPS_PREFIX + MAIL_HOST) + 
      SEARCH_PREFIX +
      encodeURIComponent(query),
      // Use window name so that if left open, the instance will be reused and
      // Gmail doesn't have to be reloaded
      "mail-triends-" + MAIL_HOST);
}

function addSearchLinks(selector, queryGenerator) {
  var matchingNodes = _(selector);
  
  matchingNodes.addClass("clickable");
  matchingNodes.each(function() {
    var node = this;
    node.onclick = function() {
      runSearch(queryGenerator(node));
    }
  });
}

_(function() {
  addSearchLinks(
      ".message-id", 
      function(node) {
        return node.id;
      });

  addSearchLinks(
      "td.sender, li.sender", 
      function(node) {
        return "from:" + _("span", node).get(0).title;
      });
  
  addSearchLinks(
      "td.recipient, li.recipient", 
      function(node) {
        return "to:" + _("span", node).get(0).title;
      });

  addSearchLinks(
      "td.list, li.list", 
      function(node) {
        return "listid:" + _("span", node).get(0).title;
      });

  addSearchLinks(
      "b.subject",
      function(node) {
        return "subject:" + node.title;
      });

});

/**
 * Used in conjunction with RenderNameAddress to display an email address via
 * a function call to reduce the likelyhood of scraping.
 */
function renderString(var_args) {
  var chars = [];
  for (var i = 0; i < arguments.length; i++) {
    chars.push(String.fromCharCode(arguments[i]));
  }
  
  document.write(chars.join(""));
}