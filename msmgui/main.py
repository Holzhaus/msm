#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk, Gio, Poppler, GdkPixbuf
import datetime
import msmgui.widgets.customerwindow
import msmgui.widgets.invoicewindow
import msmgui.dialogs.about
import core.pdfgenerator
class MainWindow( Gtk.ApplicationWindow ):
    def __init__( self, application, database ):
        Gtk.ApplicationWindow.__init__( self, application=application )
        self.set_property( "window_position", Gtk.WindowPosition.CENTER )
        self.set_property( "default_width", 900 )
        self.set_property( "default_height", 650 )

        """FIXME: Setting an icon from stock is quite hackish.
           Read this if you want more details:
           https://mail.gnome.org/archives/gtk-app-devel-list/2007-September/msg00163.html"""
        image = Gtk.Image();
        pixbuf = image.render_icon( "gtk-find-and-replace", Gtk.IconSize.DIALOG, None );
        self.set_default_icon( pixbuf )
        # Set the window title
        self.set_title( "POSITIONs-Manager" )
        self.set_wmclass( "POSITIONs-Manager", "POSITIONs-Manager" )
        # Build GUI
        self.builder = Gtk.Builder()
        self.builder.add_from_file( "data/ui/main.glade" )
        self.builder.get_object( "content" ).reparent( self )
        self.builder.connect_signals( self )

        self._customerwindow = msmgui.widgets.customerwindow.CustomerWindow()
        self.builder.get_object( "customerwindow" ).add( self._customerwindow )
        self._customerwindow.connect( "status-changed", self.statusbar_cb )

        self._invoicewindow = msmgui.widgets.invoicewindow.InvoiceWindow()
        self.builder.get_object( "invoicewindow" ).add( self._invoicewindow )
        self._invoicewindow.connect( "status-changed", self.statusbar_cb )

        self._aboutdialog = msmgui.dialogs.about.AboutDialog( self )

        """MenuBar Actions"""
        about_action = Gio.SimpleAction.new( "about", None )
        about_action.connect( "activate", self.about_cb )
        self.add_action( about_action )

        self.manager = database
    def add_status_message( self, message ):
        statusbar = self.builder.get_object( "statusbar" )
        context_id = statusbar.get_context_id( message )
        statusbar.push( context_id, message )
        return context_id
    """Callbacks for MenuBar Actions"""
    def about_cb( self, action, parameter ):
        self._aboutdialog.show()
    """Callbacks"""
    def statusbar_cb( self, sender, message ):
        self.add_status_message( message )
"""    def magazines_treeview_selection_changed_cb( self, selection ):
        model, treeiter = selection.get_selected()
        if treeiter != None:
            if not model[treeiter][1]:
                # This is a magazine
                self.builder.get_object( 'magazines_entry_name' ).set_text( model[treeiter][2] )
                self.builder.get_object( 'magazines_spinbutton_issuesperyear' ).set_value( 6 )
                self.builder.get_object( 'magazines_notebook' ).set_current_page( 0 )
            else:
                # This is a subscription
                subscription = self.manager.getSubscriptionById( model[treeiter][0] )
                self.builder.get_object( 'subscriptions_name_entry' ).set_text( subscription.name )
                self.builder.get_object( 'subscriptions_value_spinbutton' ).set_value( subscription.value )
                self.builder.get_object( 'subscriptions_valuefixed_checkbutton' ).set_active( subscription.value_fixed )
                self.builder.get_object( 'subscriptions_numberofissues_spinbutton' ).set_value( subscription.number_of_issues if subscription.number_of_issues else 0 )
                self.builder.get_object( 'magazines_notebook' ).set_current_page( 1 )
    def menu_bookkeeping_automaticdebiting_imagemenuitem_activate_cb( self, menuitem ):
        customer_edit_id = None
        if self.customereditor.status != CustomerEditor.StatusType.Inactive:
            if self.customereditor.status != CustomerEditor.StatusType.Add:
                customer_edit_id = self.customereditor.status
            self.customereditor.endEdit()
        date = datetime.date.today()
        self.manager.doAutomaticDebiting( date )
        self.parent.addStatusMessage( "Automatische Sollstellung ausgeführt." )
        if customer_edit_id:
            customer = self.manager.getCustomerById( customer_edit_id )
            if customer:
                self.customereditor.startEdit( customer )
    def menu_export_directwithdrawaldata_imagemenuitem_activate_cb( self, menuitem ):
        filename = "/tmp/DTAUS0.txt"
        format = 'DTA'
        self.manager.exportBankTransactions( filename, format, creation_date=datetime.date.today(), execution_date=datetime.date.today() )
    def menu_export_shippingdata_imagemenuitem_activate_cb( self, menuitem ):
        filename = "/tmp/export.csv"
        date = datetime.date.today()
        rows = self.manager.exportShippingData( filename, date )
        self.parent.addStatusMessage( ( "Einen Datensatz für Postverschickung exportiert." if rows == 1 else "%d Datensätze für Postverschickung exportiert." % rows ) )
    def menu_import_deutschepostcsv_imagemenuitem_activate_cb( self, menuitem ):
        assistant = self.builder.get_object( 'assistant_import_deutschepostcsv' )
        for i in range( assistant.get_n_pages() ):
            assistant.set_page_complete( assistant.get_nth_page( i ), False )
        self.builder.get_object( 'assistant_import_deutschepostcsv_open_entry' ).set_text( '' )
        assistant.show()
    def menu_import_spardabankxls_imagemenuitem_activate_cb( self, menuitem ):
        filename = "/tmp/test.xls"
        self.manager.importBankTransactions( filename )
    def menu_manager_save_imagemenuitem_activate_cb( self, menuitem ):
        if self.customereditor.endEdit():
            if self.manager.session_changed():
                self.manager.save()
    def menu_manager_clearcustomers_imagemenuitem_activate_cb( self, menuitem ):
        dialog = Gtk.MessageDialog( self.builder.get_object( 'window' ), Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, "Bist du sicher?" )
        dialog.format_secondary_text( "Bist du sicher, dass du alle Kundendaten löschen willst?" )
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.manager.save()
            backup = False
            dburl = urllib.parse.urlparse( self.parent.config.get( 'Database', 'database_uri' ) )
            filename = ""
            if dburl.scheme == "sqlite" and os.path.exists( dburl.path[1:] ):
                if not os.path.exists( self.parent.config.get( 'General', 'backup_path' ) ):
                    os.mkdir( self.parent.config.get( 'General', 'backup_path' ) )
                if os.path.exists( self.parent.config.get( 'General', 'backup_path' ) ):
                    filename = os.path.join( self.parent.config.get( 'General', 'backup_path' ), datetime.datetime.now().strftime( "backup-%Y-%m-%d-%H-%M-%S.db" ) )
                    if not os.path.exists( filename ):
                        try:
                            shutil.copy( dburl.path[1:], filename )
                            backup = True
                        except:
                            print( "Error" )
            if backup:
                self.parent.addStatusMessage( "Backup erstellt in '%s'." % filename )
                self.manager.clearCustomers()
                self.manager.save()
                self.parent.load_customerdata()
        dialog.destroy()
    def menu_manager_preferences_imagemenuitem_activate_cb( self, menuitem ):
        self.parent.load_preferencesdata()
        self.builder.get_object( 'preferences_dialog' ).show()

class CellRendererDate( Gtk.CellRendererText ):
    __gtype_name__ = 'CellRendererDate'
    def __init__( self ):
        Gtk.CellRendererText.__init__( self )
        self.date_format = '%d/%m/%Y'
        self.calendar_window = None
        self.calendar = None
    def _create_calendar( self, treeview ):
        self.calendar_window = Gtk.Dialog( parent=treeview.get_toplevel() )
        self.calendar_window.action_area.hide()
        self.calendar_window.set_decorated( False )
        self.calendar_window.set_property( 'skip-taskbar-hint', True )

        self.calendar = Gtk.Calendar()
        self.calendar.display_options( Gtk.CALENDAR_SHOW_DAY_NAMES | Gtk.CALENDAR_SHOW_HEADING )
        self.calendar.connect( 'day-selected-double-click', self._day_selected, None )
        self.calendar.connect( 'key-press-event', self._day_selected )
        self.calendar.connect( 'focus-out-event', self._selection_cancelled )
        self.calendar_window.set_transient_for( None )  # cancel the modality of dialog
        self.calendar_window.vbox.pack_start( self.calendar )

        # necessary for getting the (width, height) of calendar_window
        self.calendar.show()
        self.calendar_window.realize()
    def do_start_editing( self, event, treeview, path, background_area, cell_area, flags ):
        if not self.get_property( 'editable' ):
            return

        if not self.calendar_window:
            self._create_calendar( treeview )

        # select cell's previously stored date if any exists - or today
        if self.get_property( 'text' ):02.05.2014
            date = datetime.datetime.strptime( self.get_property( 'text' ), self.date_format )
        else:
            date = datetime.datetime.today()
            self.calendar.freeze()  # prevent flicker
            ( year, month, day ) = ( date.year, date.month - 1, date.day )  # datetime's month starts from one
            self.calendar.select_month( int( month ), int( year ) )
            self.calendar.select_day( int( day ) )
            self.calendar.thaw()

            # position the popup below the edited cell (and try hard to keep the popup within the toplevel window)
            ( tree_x, tree_y ) = treeview.get_bin_window().get_origin()
            ( tree_w, tree_h ) = treeview.window.get_geometry()[2:4]
            ( calendar_w, calendar_h ) = self.calendar_window.window.get_geometry()[2:4]
            x = tree_x + min( cell_area.x, tree_w - calendar_w + treeview.get_visible_rect().x )
            y = tree_y + min( cell_area.y, tree_h - calendar_h + treeview.get_visible_rect().y )
            self.calendar_window.move( x, y )

            response = self.calendar_window.run()
            if response == Gtk.ResponseType.RESPONSE_OK:
                ( year, month, day ) = self.calendar.get_date()
                date = datetime.date( year, month + 1, day ).strftime ( self.date_format )  # gtk.Calendar's month starts from zero
                self.emit( 'edited', path, date )
                self.calendar_window.hide()
            return None  # don't return any editable, our gtk.Dialog did the work already
    def _day_selected( self, calendar, event ):
        # event == None for day selected via doubleclick
        if not event or event.type == Gdk.KEY_PRESS and Gdk.keyval_name( event.keyval ) == 'Return':
            self.calendar_window.response( Gtk.ResponseType.RESPONSE_OK )
            return True
    def _selection_cancelled( self, calendar, event ):
        self.calendar_window.response( Gtk.ResponseType.RESPONSE_CANCEL )
        return True
"""
