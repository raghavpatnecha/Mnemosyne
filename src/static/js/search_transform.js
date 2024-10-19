;(function(window) {

	'use strict';

	var pageContainer = document.querySelector('.page'),
		openCtrl = document.getElementById('btn-search'),
		closeCtrl = document.getElementById('btn-search-close'),
		searchContainer = document.querySelector('.search'),
		inputSearch = searchContainer.querySelector('.search__input'),
		lastFocusedElement;

	function init() {
		initEvents();
// Open the search by default
		openSearch();
		// Show loaders

	}

	function initEvents() {
		
		openCtrl.addEventListener('click', openSearch);
		closeCtrl.addEventListener('click', closeSearch);
		document.addEventListener('keyup', function(ev) {
			// escape key.
			if( ev.keyCode == 27 ) {
				closeSearch();
			}
		});
	}

	function openSearch() {
		lastFocusedElement = document.activeElement;
		pageContainer.classList.add('page--move');
		searchContainer.classList.add('search--open');
		setTimeout(function() {
			inputSearch.focus();
		}, 1200);
	}

	function closeSearch() {
		pageContainer.classList.remove('page--move');
		searchContainer.classList.remove('search--open');
		inputSearch.blur();
		inputSearch.value = '';
		if (lastFocusedElement) { // restore focus
			lastFocusedElement.focus();
		}
	}

    // Expose the functions to the global scope
	window.closeSearch = closeSearch;
	window.openSearch = openSearch;
	init();

})(window);