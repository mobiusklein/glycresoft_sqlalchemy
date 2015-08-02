Application::renderHypothesisSampleMatchListAt = (container)->
    chunks = []
    template = 
    for hsm in _.sortBy(_.values(@hypothesisSampleMatches), (o) -> o.name)
        row = $("
    <div data-id=#{hsm.id} class=''>
        <span class='handle'>#{hsm.name.replace('_', ' ')}</span> <small class='right'>#{}
            <a class='remove-hsm mdi-content-clear'></a></small></div>
    ")
        chunks.push row
        self = @
        row.click (event) ->
            handle = $(@)
            id = handle.attr('data-id')
            self.addLayer ActionBook.viewDatabaseSearchResults, {hypothesis_sample_match_id: id}
            console.log self.layers
            console.log self.lastAdded
            self.context["hypothesis_sample_match_id"] = id
            self.setShowingLayer self.lastAdded

        row.find(".remove-hsm").click (event) -> 
            handle = $ @

    $(container).html chunks

Application.initializers.push ->
    @on "render-hypothesis-sample-matches", =>
        @renderHypothesisSampleMatchListAt ".hypothesis-sample-match-list"