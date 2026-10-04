/**
 * Created by hg on 23.10.2016.
 */
var isMobile = {
    Android: function() {
        return navigator.userAgent.match(/Android/i);
    },
    BlackBerry: function() {
        return navigator.userAgent.match(/BlackBerry/i);
    },
    iOS: function() {
        return navigator.userAgent.match(/iPhone|iPad|iPod/i);
    },
    Opera: function() {
        return navigator.userAgent.match(/Opera Mini/i);
    },
    Windows: function() {
        return navigator.userAgent.match(/IEMobile/i);
    },
    any: function() {
        return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Opera() || isMobile.Windows());
    }
};
 function fill() {
    if (9 * $( window ).width() > 16 * $( window ).height()) {
        $('video').css('width', '100%');
        $('video').css('height', '');
    } else {
        $('video').css('width', '');
        $('video').css('height', 'auto');
    }
}

/*видео для ie*/
$(".link-block-item__video").each(function(){
	var ht = $(this).height();
	var wh = $(this).width();
	$(this).find("video").attr("height",ht);
	$(this).find("video").attr("width",wh);
}); 
if($('body').hasClass('page-main-slider')){
	if($('#main-slider-js .main-slider__item').length > 1){
		var mainSliderCircle = new ProgressBar.Circle('#svg-circle-js', {
			strokeWidth: 2,
			//easing: 'easeInOut',
			duration: 15000,
			color: '#FFF',
			trailColor: 'transparent',
			trailWidth: 0,
			svgStyle: null
		});

		var mainSlider = $('#main-slider-js').owlCarousel({
			items:1,
			loop:true,
			margin:0,
			nav:false,
			autoplay:false,
			/*onInitialized: function(){
				mainSliderCircle.animate(1.0, { duration: 15000
				}, function() {
					mainSlider.trigger('next.owl.carousel');
				});
			},
			onTranslate: function(){
				mainSliderCircle.set(0);
			},
			onTranslated: function(){
				mainSliderCircle.animate(1.0, { duration: 15000
				}, function() {
					mainSlider.trigger('next.owl.carousel');
				});
			}*/
		});

		$('#main-slider-prev').click(function(){
			mainSlider.trigger('prev.owl.carousel');
		});
		$('#main-slider-next').click(function(){
			mainSlider.trigger('next.owl.carousel');
		});
	}
    
}

function owl1Slider() {
    $('.owl-1-js').each(function() {

            $(this).owlCarousel({
                nav:true,
                mouseDrag:true,
                responsive : {
                    0: {
                        items:1,
                        slideBy:1
                    },
                      768: {
                        items:1,
                        slideBy:1
                    },
                    1024: {
                        items:1,
                        slideBy:1
                    }
                }

            });

    });
}
function owl3Slider() {
    $('.owl-3-js').each(function() {
        if ($(this).closest('.photos-items_slider').length > 0){
        	var container = $(this).closest('.photos-items_slider');
        }else if ($(this).closest('.video-items_slider').length > 0) {
        	var container = $(this).closest('.video-items_slider');
        }
        if ($(this).find('div').length > 3) {
            $(this).owlCarousel({
                nav:true,
                loop:false,
                mouseDrag:true,
                responsive : {
                    0: {
                        items:1,
                        slideBy:1
                    },
                      768: {
                        items:3,
                        slideBy:1
                    },
                    1024: {
                        items:3,
                        slideBy:1
                    }
                },
                onInitialized: function(){
                    container.css('height', 'auto');
                    container.css('overflow', 'visible')
                }

            });
        }else{
			container.toggleClass("not-padding-slider");
			$(this).owlCarousel({
                nav:false,
                loop:false,
                mouseDrag:false,
                responsive : {
                    0: {
                        items:1,
                        slideBy:1
                    },
                      768: {
                        items:1,
                        slideBy:1
                    },
                    1024: {
                        items:1,
                        slideBy:1
                    }
                },
                onInitialized: function(){
                    container.css('height', 'auto');
                    container.css('overflow', 'visible')
                }

            });
		}

    });
}
function owl4Slider() {
    $('.owl-4-js').each(function(){
        if ($(this).closest('.photos-items_slider').length > 0){
        	var container = $(this).closest('.photos-items_slider');
        	 if($(this).find('div').length > 4){
        	}
        }else if ($(this).closest('.video-items_slider').length > 0) {
        	var container = $(this).closest('.video-items_slider');
        	if($(this).find('div').length > 4){
        	}
        }
		if ($(this).find('div').length > 3) {
            $(this).owlCarousel({
                nav:true,
                loop:false,
                mouseDrag:true,
                responsive : {
                    0: {
                        items:1,
                        slideBy:1
                    },
                      768: {
                        items:3,
                        slideBy:1
                    },
                    1024: {
                        items:4,
                        slideBy:1
                    }
                },
                onInitialized: function(){
                    container.css('height', 'auto');
                    container.css('overflow', 'visible')
                }

            });
		}else{
			container.toggleClass("not-padding-slider");
			$(this).owlCarousel({
                nav:false,
                loop:false,
                mouseDrag:false,
                responsive : {
                    0: {
                        items:1,
                        slideBy:1
                    },
                      768: {
                        items:1,
                        slideBy:1
                    },
                    1024: {
                        items:1,
                        slideBy:1
                    }
                },
                onInitialized: function(){
                    container.css('height', 'auto');
                    container.css('overflow', 'visible')
                }

            });
		}

    });

}

// if ($('.tabs-js').length && !document.location.hash) {
//     document.location.hash = $('#tab-otchet').length ? '#tab-otchet' : $('.tabs-nav li:first-child a').attr('href');
// }
$('.tabs-js').tabs({
    show: 'fade',
    hide: 'fade',
    beforeActivate: function (event, ui) {
		if( $(ui.newTab).find('a').attr('href').indexOf('#') != 0){ //check if it is hash link
        	window.open($(ui.newTab).find('a').attr('href'), '_self');
      	}
        window.location.hash = ui.newPanel.selector;
        var containerTab = ui.newPanel;
        var owl = $(containerTab).find('.owl-carousel');
        owl.trigger('destroy.owl.carousel').removeClass('owl-carousel owl-loaded');
		owl.find('.owl-stage-outer').children().unwrap();
		$('.form-styler-js').each(function(){
            $(this).styler('destroy');
        });

    },
    activate: function(event,ui){
        owl1Slider();	    
        owl3Slider();
        owl4Slider();
        formStyler();
		//$("html, body").animate({ scrollTop: 0 }, "fast");
    }

});

$('.Spec-tabs-js').tabs({
    show: 'fade',
    hide: 'fade',
    beforeActivate: function (event, ui) {
		if( $(ui.newTab).find('a').attr('href').indexOf('#') != 0 ){ //check if it is hash link
        	window.open($(ui.newTab).find('a').attr('href'), '_self');
      	}
        window.location.hash = ui.newPanel.selector;
        var containerTab = ui.newPanel;
        $('.form-styler-js').each(function(){
        $(this).styler('destroy');
        });

    },
    activate: function(event,ui){

        formStyler();
		//$("html, body").animate({ scrollTop: 0 }, "fast");
    }

});
$('.video-items__item-video').click(function(e){
	e.preventDefault();
	var video_id =$(this).attr('video_id');
	var height = $(window).height()*0.6;
	if (height >600){
		height = 600;
	}
	var width = $(window).width()*0.75;
	if (width >980){
		width = 980;
	}
    $.fancybox({
        maxWidth	: 980,
		maxHeight	: 600,
		fitToView	: false,
		width		: '85%',
		height		: '70%',
		autoSize	: false,
		closeClick	: false,
		openEffect	: 'fade',
		closeEffect	: 'fade',
        href: '/press/?VIDEO='+video_id+'&HEIGHT='+height+'&WIDTH='+width ,
        type: 'ajax'
    });
	return false;
});

function resize(){

    if( (window.innerWidth >= 1024) ){
        $('.main-menu > .container').removeClass('search-opened');
        $('.main-menu__search-js .search-btn').click(function(e){
            e.preventDefault();
            $('.main-menu > .container').addClass('search-opened');
            $(this).closest('.main-menu__search-js').toggleClass('opened');
        });
        $('.main-menu__search-overlay').click(function(e){
            e.preventDefault();
            $(this).closest('.main-menu__search-js').removeClass('opened');
            setTimeout(function(){
                $('.main-menu > .container').removeClass('search-opened');
            }, 500);


        });
        	$('.tabs-js ').find('.tabs-nav li').prop('style',false);
    }

if( (window.innerWidth < 1024) ){
    $('.main-menu-js').appendTo($('#mobile-menu-js .mobile-menu__inner'));
    $('.header-top__right-js').appendTo($('#mobile-menu-js .mobile-menu__inner'));
    $('#mobile-menu-js .mobile-menu__container .phone-info-block').insertAfter($('#mobile-menu-js .mobile-menu__container .top-menu'));

// $('.tabs-js').find('li.ui-state-active').css('display','none');

}else {
     $('.main-menu-js').insertAfter($('.main-menu__mobile'));
      $('.header-top__right-js').insertAfter($('.header-top__left'));
      $('.header-top__right-js .phone-info-block').insertBefore('.header-top__right-js .top-menu');
}



}

 $('.main-menu-js .main-menu__menu .has-dropdowm > a ').click(function(e){
    if( (window.innerWidth < 1024) ){
        var item = $(this).closest('.has-dropdowm');
        if(item.is('.dropdown-opened')){
            item.removeClass('dropdown-opened');
            item.find('.main-menu-dropdown').first().slideUp();
            e.preventDefault();
        }
        else{
            item.addClass('dropdown-opened');
            item.find('.main-menu-dropdown').first().slideDown();
            e.preventDefault();
        }
    }
    });


resize();
$(window).resize(function() {
     $('.form-styler-js').trigger('refresh');
     
    resize();
});

if (window.innerWidth >= 1024) {
    if($(this).find('.tabs-nav ul li').length <= 3)
    {
        /*$(this).closest('.tabs-nav:not(.news-tabs-menu)').addClass('tabs-nav-justify');*/
		$('.tabs-nav:not(.news-tabs-menu)').addClass('tabs-nav-justify');
    }
}

$('.tabs-js').not('.tabs-nav-select, .tabs-ajax-js').each(function(){
    var tabsContainer = $(this).find('.tabs-nav');
    var tabsDrop = tabsContainer.find('.ui-tabs-nav');
    var activeTab = tabsContainer.find('.ui-tabs-active');
    var currTab = tabsContainer.find('.tabs-nav__curr-tab');
    var currTabTxt = tabsContainer.find('.tabs-nav__curr-tab-txt');
    currTabTxt.text(activeTab.text());
    tabsContainer.removeClass('tabs-nav_opened');
		console.log(activeTab);
    if(window.innerWidth < 1024){
    	    tabsContainer.find('.ui-state-active').css('display','none');
    }
    
    tabsDrop.find('li a').click(function (e) {
                currTabTxt.text($(this).text());
                tabsContainer.removeClass('tabs-nav_opened');
                 if(window.innerWidth < 1024){
                 	$(this).closest('li').css('display', 'none');
					tabsDrop.find('li').not($(this).closest('li')).css('display','block');
                 }
               
                e.stopPropagation();
            });
            currTab.click(function (e) {
                tabsContainer.toggleClass('tabs-nav_opened');
                e.stopPropagation();
            })
});

function loadAjaxTab(tabId) {
    $('.tab-ajax-container').html('Загрузка...');
    $.ajax({
        url: window.location.pathname, // Replace with your actual endpoint
        method: 'POST',
        data: { tab: tabId },
        success: function(response) {
            $('#tab-' + tabId + ' .tab-ajax-container').html(response);
            $('#tab-' + tabId + ' .tab-ajax-container .accordion-js').each(function(){
                $(this).accordion({
                    collapsible: true,
                    active:false,
                    heightStyle:'content'
                });
            });
        },
        error: function() {
            console.error('Failed to fetch data for tab: ' + tabId);
        }
    });
}

$('.tabs-js.tabs-ajax-js').each(function(){
    var tabsContainer = $(this).find('.tabs-nav');
    var tabsDrop = tabsContainer.find('.ui-tabs-nav');
    var activeTab = tabsContainer.find('.ui-tabs-active');
    var currTab = tabsContainer.find('.tabs-nav__curr-tab');
    var currTabTxt = tabsContainer.find('.tabs-nav__curr-tab-txt');
    currTabTxt.text(activeTab.text());
    tabsContainer.removeClass('tabs-nav_opened');
		console.log(activeTab);
    if(window.innerWidth < 1024){
    	    tabsContainer.find('.ui-state-active').css('display','none');
    }

    if (window.location.hash) {
        var hash = window.location.hash.substring(1); // Remove the #
        var tabId = hash.replace('tab-', ''); // Extract the tab ID
        loadAjaxTab(tabId);
    }
    
    tabsDrop.find('li a').click(function (e) {
        currTabTxt.text($(this).text());
        tabsContainer.removeClass('tabs-nav_opened');

        var tabId = $(this).data('tab');
        loadAjaxTab(tabId);

        if(window.innerWidth < 1024){
        	$(this).closest('li').css('display', 'none');
		    tabsDrop.find('li').not($(this).closest('li')).css('display','block');
        }
       
        e.stopPropagation();
    });

    currTab.click(function (e) {
        tabsContainer.toggleClass('tabs-nav_opened');
        e.stopPropagation();
    })
});

$('.tabs-js .tabs-nav-select').each(function(){
    var tabsContainer = $(this);
    var tabsDrop = tabsContainer.find('.ui-tabs-nav');
    var activeTab = tabsContainer.find('.ui-tabs-active');
    var currTab = tabsContainer.find('.tabs-nav__curr-tab');
    var currTabTxt = tabsContainer.find('.tabs-nav__curr-tab-txt');
	 tabsContainer.removeClass('tabs-nav_opened');
	   if(window.innerWidth < 1024){
		  tabsContainer.find('.ui-state-active').css('display','none');        
	   }
    currTabTxt.text(activeTab.text());
    if(tabsContainer.is('.tabs-nav-select-width')){
    	tabsContainer.css('width', tabsContainer.width());
    	tabsContainer.addClass('is-sized');
    } else{
    	tabsContainer.addClass('is-sized');
    }
    tabsDrop.find('li a').click(function (e) {
        currTabTxt.text($(this).text());
        tabsContainer.removeClass('tabs-nav_opened');
        if(window.innerWidth < 1024){
                 	$(this).closest('li').css('display', 'none');
               tabsDrop.find('li').not($(this).closest('li')).css('display','block');
                 }
        e.stopPropagation();
    });

    currTab.click(function (e) {
        tabsContainer.toggleClass('tabs-nav_opened');
        e.stopPropagation();
    });

});


$('#main-menu-toggle-js').click(function(){
    $('#mobile-menu-js').addClass('mobile-menu_open');
    $('body').css('overflow','hidden');
});


$('#mobile-menu__close-js').click(function(){
    $('#mobile-menu-js').removeClass('mobile-menu_open');
    $('body').css('overflow','');
});

  
function formStyler(){
$('.form-styler-js').each(function(){
    $(this).styler({
        selectSmartPositioning:false
    });
    $(this).closest('.jq-selectbox').addClass('form-styled');
    var heightSelect = $(this).closest('.jq-selectbox').find('.jq-selectbox__select-text').width() + 10;
    $(this).closest('.jq-selectbox:not(.select-block)').find('.jq-selectbox__select-text').css('width', heightSelect+'px');
});
}
formStyler();


$('.js-validation-form').each(function() {
    var $form = $(this);
    $form.validate({
        ignore: '.ignore, :hidden :disabled',
        errorPlacement: function(error, element) {
            if ($(element).parents('.jq-selectbox').length) {
                error.insertAfter($(element).parents('.jq-selectbox'));
            } else if ($(element).is(':checkbox') || $(element).is(':radio')) {
                error.insertAfter($(element).closest('label'));
            } else if ($(element).parents('.jq-file').length) {
                error.insertAfter($(element).parents('.jq-file'));
            } else {
                error.insertAfter(element);
            }
        }
    });
});
$('[name=internet_priem]').each(function() {
    var $form = $(this);
    $form.validate({
        ignore: '.ignore, :hidden :disabled',
        errorPlacement: function(error, element) {
            if ($(element).parents('.jq-selectbox').length) {
                error.insertAfter($(element).parents('.jq-selectbox'));
            } else if ($(element).is(':checkbox') || $(element).is(':radio')) {
                error.insertAfter($(element).closest('label'));
            } else if ($(element).parents('.jq-file').length) {
                error.insertAfter($(element).parents('.jq-file'));
            } else {
                error.insertAfter(element);
            }
        }
    });
});
$('[name=waiting]').each(function() {
    var $form = $(this);
    $form.validate({
        ignore: '.ignore, :hidden :disabled',
        errorPlacement: function(error, element) {
            if ($(element).parents('.jq-selectbox').length) {
                error.insertAfter($(element).parents('.jq-selectbox'));
            } else if ($(element).is(':checkbox') || $(element).is(':radio')) {
                error.insertAfter($(element).closest('label'));
            } else if ($(element).parents('.jq-file').length) {
                error.insertAfter($(element).parents('.jq-file'));
            } else {
                error.insertAfter(element);
            }
        },
		messages:{
			yourname:{
				required: "поле не заполнено или заполнено не верно",
			},
			msg: "поле не заполнено или заполнено не верно",
			required: "поле является обязательным",
			phone: "поле не заполнено или заполнено не верно",
			theme: "поле не заполнено или заполнено не верно",
			checkbox3: "отметьте один из флажков",
			yourmail: "поле не заполнено или заполнено не верно"
		}
    });
});
jQuery.extend(jQuery.validator.messages, {
    email: "E-mail введен некорректно. Пожалуйста, исправьте.",
});

$.datepicker.regional['ru'] = {
    closeText: 'Закрыть',
    prevText: '&#x3c;Пред',
    nextText: 'След&#x3e;',
    currentText: 'Сегодня',
    monthNames: ['Январь','Февраль','Март','Апрель','Май','Июнь',
        'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'],
    monthNamesShort: ['Янв','Фев','Мар','Апр','Май','Июн',
        'Июл','Авг','Сен','Окт','Ноя','Дек'],
    dayNames: ['воскресенье','понедельник','вторник','среда','четверг','пятница','суббота'],
    dayNamesShort: ['вск','пнд','втр','срд','чтв','птн','сбт'],
    dayNamesMin: ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'],
    dateFormat: 'dd.mm.yy',
    firstDay: 1,
    isRTL: false
};
$.datepicker.setDefaults($.datepicker.regional['ru']);
$('.datepicker-js').datepicker({
    language: "ru",
    nextText: ">",
    prevText: "<"
});

$('input, textarea').placeholder();


$( ".accordion-js").each(function(){
    $(this).accordion({
    collapsible: true,
    active:false,
    heightStyle:'content'
});

});





$('body').click(function(e){
    $('.tabs-nav-select').each(function(){
        if ($(this).hasClass('tabs-nav_opened')){
            $(this).removeClass('tabs-nav_opened');
        }
    });
    $('.tabs-js .tabs-nav').each(function(){
        if ($(this).hasClass('tabs-nav_opened')){
            $(this).removeClass('tabs-nav_opened');
        }
    });
});











$('.menu-category-js .menu-category__toggle').click(function(){
    $('.menu-category-js').toggleClass('is-opened');
});

$(window).bind('scroll', function() {
    if($('.content-js').length > 0 && $(window).scrollTop() >= $('.content-js').offset().top  && true) {
        $('.menu-category-js').addClass('menu-category_fixed');
        $('.menu-category-js').removeClass('is-opened');
    }
    else{
        $('.menu-category-js').removeClass('menu-category_fixed');
    }
});

$(window).load(function() {   
      function getAndroidVersion(ua) {
        ua = (ua || navigator.userAgent).toLowerCase(); 
        var match = ua.match(/android\s([0-9\.]*)/);
        return match ? match[1] : false;
    };
     
    if(parseInt(getAndroidVersion(), 10) >= 6){
        $('.video-click-js').removeClass('active');
    }

   
    var isIOS = /iPad|iPhone|iPod/.test(navigator.platform);
	
	
	
	
	if (isIOS) {
		$(".video-click-btn").css("display","none");
	}
    if($('.video-canvas').length){
		if (isIOS) {
			//document.querySelectorAll('.video-canvas')[0].style.display = 'block';
			
			var canvasVideo = new CanvasVideoPlayer({
				videoSelector: 'video',
				canvasSelector: '.video-canvas', 
				
				});

		}else {

			// Use HTML5 video
			document.querySelectorAll('.video-canvas')[0].style.display = 'none';
		}
	}
	
//$('#main-slider-js').find('video').get(0).play();


  
    $(function(){
        if($('.content-js').length>0 && $(window).scrollTop() >= $('.content-js').offset().top  && true) {
            $('.menu-category-js').addClass('menu-category_fixed');
            $('.menu-category-js').removeClass('is-opened');
        }
        else{
            $('.menu-category-js').removeClass('menu-category_fixed');
        }
    });
owl1Slider()
owl3Slider();
owl4Slider();

$(document).on('click', '.cookie__button', function (e) {
    $.cookie('cookie', 'Y', { expires: 30, path: '/' });
    $('.cookie').fadeOut();
});

});

$(".video-hover-js").each(function(){
	if($(this).find(".link-block-item__img_ad").length > 0){
		var videoOnHover = $(this).hover( hoverVideoPlay, hoverVideoPause);
		function hoverVideoPlay() {
			$('video', videoOnHover).get(0).play();
		}
		function hoverVideoPause() {
			$('video', videoOnHover).get(0).pause();
		}
	}else{
		var videoOnHover2 = $(this).hover( hoverVideoPlay2, hoverVideoPause2);
		function hoverVideoPlay2() {
			$('video', videoOnHover2).get(0).play();
		}
		function hoverVideoPause2() {
			$('video', videoOnHover2).get(0).pause();
		}
	}
	
	
});

$('.video-click-js .video-click-info').each(function(e){
    var container = $(this).closest('.video-click-js');
    var video = $(this).closest('.video-click-js').find('video').get(0);
   $(this).on('click',function (e) {
    
     if (video.paused === false) {
        video.pause();
        $(this).css('opacity','1');
        $(this).closest('.video-click-js').toggleClass('active');
    } else {
        video.play();
        $(this).css('opacity','0');
        $(this).closest('.video-click-js').toggleClass('active');
    }
    return false;
}); 
});

 


$('.owl-pokazateli-slider-js').on('initialized.owl.carousel', function(e){
    idx = e.item.index;
    $('.owl-item').find('.slider-item').removeClass('animated zoomIn active');
    $('.owl-item').eq(idx).find('.slider-item').addClass('animated zoomIn active ');
    $('.owl-item').eq(idx+1).find('.slider-item').addClass('animated zoomIn active ');
    $('.owl-item').eq(idx+2).find('.slider-item').addClass('animated zoomIn active ');
});

$(".owl-pokazateli-slider-js").owlCarousel({
    addClassActive: true,
    nav:true,
    loop:false,
    mouseDrag:true,
    responsive : {
        0: {
            items:1,
            slideBy:1
        },
        768: {
              items:2,
              slideBy:2
        },
        1024: {
            items:3,
            slideBy:1
        }
    }

});

$('.owl-pokazateli-slider-js').on('translated.owl.carousel', function(e){
    idx = e.item.index;
    $('.owl-item').find('.slider-item').removeClass('animated zoomIn active');
    $('.owl-item').eq(idx).find('.slider-item').addClass('animated zoomIn active ');
    $('.owl-item').eq(idx+1).find('.slider-item').addClass('animated zoomIn active ');
    $('.owl-item').eq(idx+2).find('.slider-item').addClass('animated zoomIn active ');
});



new WOW().init();

$('.sverhy').each(function(){
    $(this).next('.snizy').slideUp('1s');
 });

$('.sverhy').click(function(){
   $(this).next('.snizy').slideToggle('1s');
    return false;
});

 (function(){
    if (typeof WebFont != 'undefined') {
        WebFontConfig = {
            custom: {
                families: ['Geometria']
            },
            active: function() {
                $('select, :checkbox, :radio').trigger('refresh');
				console.log("fff");
            }
        };
        WebFont.load(WebFontConfig);
		console.log("ff");
		setTimeout(function(){formStyler();}, 500);
    }else{
		//console.log("undefined");
	}
})();

$('input[type="file"]').bind('change',function(){
    var inputVal = this.value.replace(/^.*\\/, "");
    $(this).closest('.btn-file').find('.btn-file-val').text(inputVal);
});

function initMapCompanyMarkers() {
    var map = new google.maps.Map(document.getElementById('map-company'), {
        zoom: 8,
        center: {lat: 55.755826, lng: 37.617300},
        disableDefaultUI: true,
        scrollwheel: false
    });

     map.setOptions({
        styles: [
            {
                "featureType": "administrative",
                "elementType": "labels.text.fill",
                "stylers": [
                    {
                        "color": "#1d68a1"
                    }
                ]
            },
            {
                "featureType": "administrative",
                "elementType": "labels.text.stroke",
                "stylers": [
                    {
                        "color": "#ffffff"
                    }
                ]
            },
            {
                "featureType": "administrative.country",
                "stylers": [
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "administrative.land_parcel",
                "stylers": [
                    {
                        "visibility": "off"
                    }
                ]
            },
            {
                "featureType": "administrative.locality",
                "stylers": [
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "administrative.neighborhood",
                "stylers": [
                    {
                        "visibility": "off"
                    }
                ]
            },
            {
                "featureType": "administrative.province",
                "stylers": [
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "landscape",
                "stylers": [
                    {
                        "color": "#f2f2f2"
                    },
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "poi",
                "stylers": [
                    {
                        "visibility": "off"
                    }
                ]
            },
            {
                "featureType": "road.highway",
                "stylers": [
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.fill",
                "stylers": [
                    {
                        "saturation": -100
                    },
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [
                    {
                        "visibility": "off"
                    }
                ]
            },
            {
                "featureType": "road.highway",
                "elementType": "labels.icon",
                "stylers": [
                    {
                        "saturation": -100
                    },
                    {
                        "visibility": "on"
                    }
                ]
            },
            {
                "featureType": "transit",
                "stylers": [
                    {
                        "visibility": "off"
                    }
                ]
            },
            {
                "featureType": "water",
                "stylers": [
                    {
                        "color": "#ffffff"
                    }
                ]
            }
        ]
    });


    function CustomMarker(latlng, map, args) {
        this.latlng = latlng;
        this.args = args;
        this.setMap(map);
    }
    CustomMarker.prototype = new google.maps.OverlayView();
    CustomMarker.prototype.draw = function() {
        var self = this;
        var div = this.div;
        if (!div) {
            var markerTxt = 'marker';
            var markerRight = false;
            div = this.div = document.createElement('div');
            div.className = 'map-marker';
            div.innerHTML = '<a><span>' + markerTxt+ '</span></a>';

            if (typeof(self.args.marker_id) !== 'undefined') {
                div.dataset.marker_id = self.args.marker_id;
            }

            if (typeof(self.args.markerTxt) !== 'undefined') {
                div.innerHTML = '<a><span>' + self.args.markerTxt+ '</span></a>';
            }
            if (self.args.markerRight == true) {
                div.className = 'map-marker map-marker_right';
            }

            /*  google.maps.event.addDomListener(div, "click", function(event) {
             alert('You clicked on a custom marker!');
             google.maps.event.trigger(self, "click");
             });*/

            var panes = this.getPanes();
            panes.overlayImage.appendChild(div);
        }

        var point = this.getProjection().fromLatLngToDivPixel(this.latlng);

        if (point) {
            div.style.left = (point.x - 15) + 'px';
            div.style.top = (point.y - 80) + 'px';

            if (self.args.markerRight == true) {
                div.style.left = (point.x - 155) + 'px';
            }
        }
    };
    CustomMarker.prototype.remove = function() {
        if (this.div) {
            this.div.parentNode.removeChild(this.div);
            this.div = null;
        }
    };
    CustomMarker.prototype.getPosition = function() {
        return this.latlng;
    };

    new CustomMarker(
        new google.maps.LatLng(55.804368,37.836914),map,
        {
            marker_id: '1',
            markerTxt: 'Московские<br>кабельные<br>и высокольтные сети'
        }
    );

    new CustomMarker(
        new google.maps.LatLng(56.101152,37.260132),map,
        {
            marker_id: '3',
            markerTxt: 'Северные<br>электрические<br>сети'
        }
    );
    new CustomMarker(
        new google.maps.LatLng(55.020150,37.183228),map,
        {
            marker_id: '5',
            markerTxt: 'Южные<br>электрические<br>сети'
        }
    );
    new CustomMarker(
        new google.maps.LatLng(55.662095,35.480347),map,
        {
            marker_id: '6',
            markerTxt: 'Западные<br>электрические<br>сетии'
        }
    );
    new CustomMarker(
        new google.maps.LatLng(55.422779,36.974487),map,
        {
            marker_id: '7',
            markerTxt: 'Новая Москва'
        }
    );
    new CustomMarker(
        new google.maps.LatLng(55.634198,39.078369),map,
        {
            marker_id: '8',
            markerTxt: 'Восточные<br>электрические<br>сети'
        }
    );

}





    $(document).ready(function(){
        $('.chocolat-js').Chocolat({
                afterMarkup: function () {
                this.elems.description.prependTo(this.elems.bottom);
            }
        });
        $(function($){
            $.mask.definitions['~']='[+-]';
            $('.phone-mask-js').mask('+7 (999) 999-9999');
			$('.phone-mask-js-wo').mask('+79999999999');
        });


		/*(function() {
		var path = '//easy.myfonts.net/v2/js?sid=250385(font-family=Geometria+Bold)&sid=250387(font-family=Geometria+ExtraLight)&sid=250395(font-family=Geometria+Medium)&sid=250397(font-family=Geometria)&key=s8dI0kxavU',
		protocol = ('https:' == document.location.protocol ? 'https:' : 'http:'),
		trial = document.createElement('script');
		trial.type = 'text/javascript';
		trial.async = true;
		trial.src = protocol + path;
		var head = document.getElementsByTagName("head")[0];
		head.appendChild(trial);
		})();*/

		formStyler();
    });


$('.textarea-count-js').each(function(){
    var maxLenght = $(this).prop('maxlength');
    var countContainer = $(this).parent('.form-field').find('.textarea-counter');
    countContainer.text('Осталось ' +maxLenght+ ' символов');
    $(this).keyup(function(){
        var currLenght = $(this).val().length;
        var remainingLenght = maxLenght - currLenght;
        countContainer.text('Осталось ' +remainingLenght+ ' символов');
    });
});


$(".fancybox").fancybox({
    maxWidth	: 980,
    maxHeight	: 600,
    fitToView	: false,
    width		: '85%',
    height		: '70%',
    autoSize	: false,
    closeClick	: false,
    openEffect	: 'fade',
    closeEffect	: 'fade'
});
$(".img_reiting").fancybox({
    maxWidth	: 980,
    maxHeight	: 600,
    fitToView	: false,
    width		: '85%',
    height		: '70%',
    autoSize	: false,
    closeClick	: false,
    openEffect	: 'fade',
    closeEffect	: 'fade'
});
$(".file-link_audio").fancybox({
    maxWidth	: 680,
    maxHeight	: 400,
    fitToView	: false,
    width		: '85%',
    height		: '70%',
    autoSize	: false,
    closeClick	: false,
    openEffect	: 'fade',
    closeEffect	: 'fade'
});
$(".about-doc_img").fancybox({
    maxWidth		: '90%',
    maxHeight		: '90%',
    closeClick	: false,
    openEffect	: 'fade',
    closeEffect	: 'fade'
});


if($('.page-banner-js .item').length > 1){
	$('.page-banner-js').owlCarousel({
		nav:true,
		loop:true,
		mouseDrag:true,
		responsive : {
			0: {
				items:1,
				slideBy:1
			},
			768: {
				  items:1,
				  slideBy:1
			},
			1024: {
				items:1,
				slideBy:1
			}
		}
	});
}

$('.specQuoteSlider').owlCarousel({
	nav:true,
	loop:true,
	mouseDrag:true,
	dots:true,
	responsive : {
		0: {
			items:1,
			slideBy:1,
			nav:false
		},
		768: {
			  items:1,
			  slideBy:1,
			nav:false			  
		},
		1024: {
			items:1,
			slideBy:1,
			nav: true
		}
	}
});

//$(".tabs-nav-inline ul li").removeClass("ui-tabs-active ui-state-active");
$(".tabs-nav-inline ul li:last-child").trigger("click");
$("[name=form_radio_obrachenie]").on("change",function(){
	if($(this).val() == 82){
		$(".srok span").text("10 рабочих дней");
	}else{
		$(".srok span").text("3 рабочих дня");
	}
});
$('.radio_change').click(function () {
            $(this).prev().children('input').click();
        });

        $('[name=radio_change]').change(function () {
            var val = $(this).val();
            if (val == 1) {
                $('#1').addClass('active_form');
                $('#2').removeClass('active_form');
            } else {
                $('#2').addClass('active_form');
                $('#1').removeClass('active_form');
            }
        });
  function KeyboardBehaviour(obj) {
        var languageRule = {
            oldCharachters: 'qwertyuiop[]asdfghjkl;\'zxcvbnmQWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>~`',
            newCharachters: 'йцукенгшщзхъфывапролджэячсмитьЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁё'
        };
        var digitalRule = {
            oldCharachters: '\\',
            newCharachters: ''
        };
        var rules = [languageRule, digitalRule];
        obj.keypress(
            function (e) {
                var o = $(this);
                setTimeout(function () {
                    var oldText;
                    var text = '';
                    for (var k = 0; k < rules.length; k++) {
                        var rule = rules[k];
                        oldText = text == '' ? e.currentTarget.value : text;
                        text = '';
                        for (var i = 0; i < oldText.length; i++) {
                            var ch = oldText[i];
                            var id = rule.oldCharachters.indexOf(ch);
                            text += id >= 0 ? id < rule.newCharachters.length ? rule.newCharachters[id] : '' : ch;
                        }
                    }
                    if (text != e.currentTarget.value) {
                        onTextUpdate(text, o, e);
                    }
                }, 0);
            });

        function onTextUpdate(text, o, e) {
            var start = getCursorPosition(o);
            e.currentTarget.value = text;
            if (start != undefined)
                setCursorPosition(o, start);
        }
        function setCursorPosition(element, pos) {
            if (element.get(0).setSelectionRange) {
                element.get(0).setSelectionRange(pos, pos);
            } else if (element.get(0).createTextRange) {
                var range = element.get(0).createTextRange();
                range.collapse(true);
                range.moveEnd('character', pos);
                range.moveStart('character', pos);
                range.select();
            }
        }

        function getCursorPosition(element) {
            var el = element.get(0);
            var pos = 0;
            if ('selectionStart' in el) {
                pos = el.selectionStart;
            } else if ('selection' in document) {
                el.focus();
                var sel = document.selection.createRange();
                var selLength = document.selection.createRange().text.length;
                sel.moveStart('character', -el.value.length);
                pos = sel.text.length - selLength;
            }
            return pos;
        }
    }
//ВЫЗОВ ОБРАБОТЧИКА ДЛЯ ЛАТИНИЦЫ
KeyboardBehaviour($(".ConvertToRussian"));
$.mask.definitions['r']='[А-Яа-я]';
	$.mask.definitions['e']='[А-Яа-я0-9]';
$(".zayavkaNumber").mask("r-99-99-999999/999/ee")

$(document).ready(function(){
	var totop = true;
	if (location.hash && totop) {               
       // window.scrollTo(0, 0);         
        setTimeout(function() {
			
            window.scrollTo(0, 0); 
			totop = false;
        }, 10);
    }
	

});
if	(window.innerWidth < 570) {
	//var img = $(".video-click-js").find("img").attr("src");
	//$(".video-click-js").closest(".main-slider__item").css("background","url("+img+")");
	//$(".video-click-js").closest(".main-slider__item").css("background-position","center");
		
}
$(function () {
	if($(".ui-tabs-nav").length){
		var hash = $.trim( window.location.hash );
		if(hash){
			$(".tabs-content:eq(0)").children(".ui-widget-content").each(function(){
				$(this).css("display","none");
			});
		$("" + hash + "").css('display','block');
		}
		
	}

	$('.tab-external-link').unbind('click');

    if ($('.js-show-iframe').length > 0) {
        $('.js-show-iframe').on('click', function() {
            var $this = $(this);
            var iframe = $this.data('iframe');
    
            $this.parent().append(iframe);
            $this.remove();
        });
    }

    $('.banner-slider').each(function() {
	if ($(this).find('div').length > 1) {
            $(this).owlCarousel({
		autoplay:true,
		loop:true,
                nav:true,
                mouseDrag:true,
		items:1,
                slideBy:1,
            });
	}
    });
}); 


