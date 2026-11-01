//Custom validation script for the RequiredIfTrue validator
/*
 * Note that, jQuery validation registers its rules before the DOM is loaded. 
 * If you try to register your adapter after the DOM is loaded, your rules will
 * not be processed. So wrap it in a self-executing function.
 * */
(function ($) {

    const $jQval = $.validator;

    $jQval.addMethod("requirediftrue",
        function (value, element, parameters) {
            return value !== "" && value != null;
        }
    );

    const adapters = $jQval.unobtrusive.adapters;
    adapters.addBool('requirediftrue');

})(jQuery);