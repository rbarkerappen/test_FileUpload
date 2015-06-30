function FileUpload(params) {
	this.fileUploadID = null;
	this.originalFilename = null;
	this.savedFilename = null;
	this.url = null;
	this.uploaded = null;
	this.deleteURL = null;
	if(params)
		this.populate(params);
}

FileUpload.prototype.populate = function(params) {
	this.fileUploadID = params.fileUploadID;
	this.originalFilename = params.originalFilename;
	this.savedFilename = params.savedFilename;
	this.url = params.url;
	this.uploaded = params.uploaded;
	this.deleteURL = params.deleteURL;
}

FileUpload.prototype.build = function() {
	var row = $("<tr class='file-upload'><td class='id'></td><td class='filename'><a target='_blank'></a></td><td class='delete'><a>Delete</a></td></tr>");
	row.find("td.id").text(this.fileUploadID);
	row.find("td.filename a").attr("href", this.url).text(this.originalFilename);
	row.find("td.delete a").attr("href", this.deleteURL).click(function(ev) {
		
		ev.preventDefault();

		var row = $(this).parents("tr.file-upload");
		var url = $(this).attr("href");

		var answer = confirm("Are you sure you want to delete this uploaded file?");
		if(!answer)
			return;

		$.ajax({
			url: url,
			type: "DELETE",
			dataType: 'json',
		
			error: function(d) {
				alert("Unable to delete file.");
			},
		
			success: function (response) {
				row.remove();
			}
		});
	});
	
	return row;
}


$(document).ready(function(ev) {
	
	// create rows for file uploads
	var uploads = $("#uploads");

	for(var i = 0; i < fileUploads.length; i++) {
		var fileUpload = new FileUpload(fileUploads[i]);
		uploads.append(fileUpload.build());
	}
});




$(function(){

    var ul = $('#upload ul');

    $('#drop a').click(function(){
        // Simulate a click on the file input button
        // to show the file browser dialog
        $(this).parent().find('input').click();
    });

    // Initialize the jQuery File Upload plugin
    $('#upload').fileupload({

        // This element will accept file drag/drop uploading
        dropZone: $('#drop'),

        // This function is called when a file is added to the queue;
        // either via the browse button, or via drag/drop:
        add: function (e, data) {

            var tpl = $('<li class="working"><input type="text" value="0" data-width="48" data-height="48"'+
                ' data-fgColor="#0788a5" data-readOnly="1" data-bgColor="#3e4043" /><p></p><span></span></li>');

            // Append the file name and file size
            tpl.find('p').text(data.files[0].name)
                         .append('<i>' + formatFileSize(data.files[0].size) + '</i>');

            // Add the HTML to the UL element
            data.context = tpl.appendTo(ul);

            // Initialize the knob plugin
            tpl.find('input').knob();

            // Listen for clicks on the cancel icon
            tpl.find('span').click(function(){

                if(tpl.hasClass('working')){
                    jqXHR.abort();
                }

                tpl.fadeOut(function(){
                    tpl.remove();
                });

            });

            // Automatically upload the file once it is added to the queue
            var jqXHR = data.submit();
        },

        progress: function(e, data){

            // Calculate the completion percentage of the upload
            var progress = parseInt(data.loaded / data.total * 100, 10);

            // Update the hidden input field and trigger a change
            // so that the jQuery knob plugin knows to update the dial
            data.context.find('input').val(progress).change();

            if(progress == 100){
                data.context.removeClass('working');
            }
        },

	success: function(e, data) {
		var added = JSON.parse(e);
		var uploads = $("#uploads");
		for(var i = 0; i < added.length; i++) {
			var fileUpload = new FileUpload(added[i]);
			uploads.append(fileUpload.build());
		}
	},

        fail:function(e, data){
            // Something has gone wrong!
            data.context.addClass('error');
        }

    });


    // Prevent the default action when a file is dropped on the window
    $(document).on('drop dragover', function (e) {
        e.preventDefault();
    });

    // Helper function that formats the file sizes
    function formatFileSize(bytes) {
        if (typeof bytes !== 'number') {
            return '';
        }

        if (bytes >= 1000000000) {
            return (bytes / 1000000000).toFixed(2) + ' GB';
        }

        if (bytes >= 1000000) {
            return (bytes / 1000000).toFixed(2) + ' MB';
        }

        return (bytes / 1000).toFixed(2) + ' KB';
    }

});
