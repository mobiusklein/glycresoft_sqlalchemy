var viewPeakGroupingDatabaseSearchResults;

viewPeakGroupingDatabaseSearchResults = function() {
  var currentPage, currentProtein, glycopeptideDetailsModal, glycopeptideTable, setup, setupGlycopeptideCompositionTablePageHandlers, showGlycopeptideCompositionDetailsModal, unload, updateGlycopeptideCompositionTablePage, updateProteinChoice;
  glycopeptideDetailsModal = void 0;
  glycopeptideTable = void 0;
  currentPage = 1;
  currentProtein = void 0;
  setup = function() {
    $('.protein-match-table tbody tr').click(updateProteinChoice);
    updateProteinChoice.apply($('.protein-match-table tbody tr'));
    return console.log("glycopeptideTable", glycopeptideTable);
  };
  setupGlycopeptideCompositionTablePageHandlers = function(page) {
    if (page == null) {
      page = 1;
    }
    $('.glycopeptide-match-row').click(showGlycopeptideCompositionDetailsModal);
    $(':not(.disabled) .next-page').click(function() {
      return updateGlycopeptideCompositionTablePage(page + 1);
    });
    $(':not(.disabled) .previous-page').click(function() {
      return updateGlycopeptideCompositionTablePage(page - 1);
    });
    return $('.pagination li :not(.active)').click(function() {
      var nextPage;
      nextPage = $(this).attr("data-index");
      if (nextPage != null) {
        nextPage = parseInt(nextPage);
        return updateGlycopeptideCompositionTablePage(nextPage);
      }
    });
  };
  updateGlycopeptideCompositionTablePage = function(page) {
    var url;
    if (page == null) {
      page = 1;
    }
    url = "/view_database_search_results/glycopeptide_matches_composition_table/" + currentProtein + "/" + page;
    console.log(url);
    return GlycReSoft.ajaxWithContext(url).success(function(doc) {
      currentPage = page;
      glycopeptideTable.html(doc);
      return setupGlycopeptideCompositionTablePageHandlers(page);
    });
  };
  updateProteinChoice = function() {
    var handle, id;
    handle = $(this);
    currentProtein = id = handle.attr('data-target');
    console.log(glycopeptideDetailsModal);
    $("#chosen-protein-container").html("<div class=\"progress\"><div class=\"indeterminate\"></div></div>").fadeIn();
    return $.post('/view_database_search_results/protein_composition_view/' + id, GlycReSoft.context).success(function(doc) {
      var tabs;
      $('#chosen-protein-container').hide();
      $('#chosen-protein-container').html(doc).fadeIn();
      tabs = $('ul.tabs');
      tabs.tabs();
      GlycReSoft.context["current_protein"] = id;
      if (GlycReSoft.context['protein-view-active-tab'] !== void 0) {
        console.log(GlycReSoft.context['protein-view-active-tab']);
        $('ul.tabs').tabs('select_tab', GlycReSoft.context['protein-view-active-tab']);
      } else {
        $('ul.tabs').tabs('select_tab', 'protein-overview');
      }
      $('.indicator').addClass('indigo');
      $('ul.tabs .tab a').click(function() {
        return GlycReSoft.context['protein-view-active-tab'] = $(this).attr('href').slice(1);
      });
      glycopeptideDetailsModal = $('#peptide-detail-modal');
      glycopeptideTable = $("#glycopeptide-table");
      return setupGlycopeptideCompositionTablePageHandlers(1);
    }).error(function(error) {
      return console.log(arguments);
    });
  };
  showGlycopeptideCompositionDetailsModal = function() {
    var handle, id;
    handle = $(this);
    id = handle.attr('data-target');
    console.log(glycopeptideDetailsModal);
    console.log(id);
    return PartialSource.glycopeptideCompositionDetailsModal({
      "id": id
    }, function(doc) {
      glycopeptideDetailsModal.find('.modal-content').html(doc);
      $(".lean-overlay").remove();
      return glycopeptideDetailsModal.openModal();
    });
  };
  unload = function() {
    return GlycReSoft.removeCurrentLayer();
  };
  return setup();
};

//# sourceMappingURL=view-peak-grouping-database-search.js.map
