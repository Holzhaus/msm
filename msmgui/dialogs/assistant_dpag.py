class ImportAssistantDPAG( object ):
		def __init__( self, params ):
				pass
		def assistant_import_deutschepostcsv_close_cb( self, assistant ):
				assistant.hide()
		def assistant_import_deutschepostcsv_apply_cb( self, assistant ):
				liststore = self.builder.get_object( 'assistant_import_deutschepostcsv_liststore' )
				importsuccess = 0
				importfail = 0
				for row in liststore:
						if row[0]:
								c = {}
								for ( i, keymap ) in enumerate( SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP ):
										key = keymap[1]
										c[key] = row[i + 1]
								customer = self.manager.addCustomer( c['familyname'], c['prename'], c['honourific'], c['title'], None, c['gender'], c['company1'], c['company2'], c['department'], flush=False )
								if customer:
										importsuccess += 1
										if set( ( "street", 'zipcode' ) ) <= c.keys():
												a = customer.addAddress( c['street'], c['zipcode'], c['city'], c['country'], c['co'], flush=False )
								else:
										importfail += 1
				if importsuccess:
						statusmessage = "%d von %d Datensätzen erfolreich importiert." % ( importsuccess, len( liststore ) )
				else:
						statusmessage = "Es wurden keine Datensätze importiert." % ( importsuccess, len( liststore ) )
				if importfail:
						statusmessage += "Beim Import von %d Datensätzen traten Fehler auf." % importfail
				self.parent.addStatusMessage( statusmessage )
				self.manager.flush()
				self.parent.load_customerdata()
				assistant.hide()
		def assistant_import_deutschepostcsv_cancel_cb( self, assistant ):
				assistant.hide()
		def assistant_import_deutschepostcsv_prepare_cb( self, assistant, page ):
				if page == assistant.get_nth_page( 1 ):
						filename = self.builder.get_object( 'assistant_import_deutschepostcsv_open_entry' ).get_text()
						importdata = SubscriptionManagerIO.csvimport( filename )
						liststore = self.builder.get_object( 'assistant_import_deutschepostcsv_liststore' )
						treeview = self.builder.get_object( 'assistant_import_deutschepostcsv_datacheck_treeview' )
						label = self.builder.get_object( 'assistant_import_deutschepostcsv_datacheck_label' )
						liststore.clear()
						if importdata:
								label.set_markup( "In der Datei <i>%s</i> wurden %d Datensätze gefunden. Hier kannst du die Daten überprüfen:" % ( os.path.basename( filename ), len( importdata ) ) )
								for customer in importdata:
										c = []
										c.append( True )
										for ( post_key, key, datatype, default ) in SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP:
												c.append( customer[key] if key in customer else default )
										liststore.append( c )
								treeview.show()
								assistant.set_page_complete( page, True )
						else:
								label.set_text( "Es konnten keine Daten gefunden werden." )
								treeview.hide()
								assistant.set_page_complete( page, False )
				elif page == assistant.get_nth_page( 2 ):
						liststore = self.builder.get_object( 'assistant_import_deutschepostcsv_liststore' )
						missing_label = self.builder.get_object( 'assistant_import_deutschepostcsv_missing_label' )
						missing = {}
						rowsfound = len( liststore )
						rowsimport = 0
						for row in liststore:
								if row[0]:
										rowsimport += 1
								for ( i, keymap ) in enumerate( SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP ):
										key = keymap[1]
										if not row[i + 1]:
												if key in missing:
														missing[key] += 1
												else:
														missing[key] = 1
						liststore_missing = self.builder.get_object( 'assistant_import_deutschepostcsv_missingdata_liststore' )
						for ( post_key, key, datatype, default ) in SubscriptionManagerIO.DEUTSCHEPOST_KEYMAP:
								if key in missing:
										liststore_missing.append( [post_key, missing[key]] )
						self.builder.get_object( 'assistant_import_deutschepostcsv_rowsfound_label' ).set_text( str( rowsfound ) )
						self.builder.get_object( 'assistant_import_deutschepostcsv_rowsimport_label' ).set_text( str( rowsimport ) )
						assistant.set_page_complete( page, True )
		def assistant_import_deutschepostcsv_open_togglebutton_toggled_cb( self, button, entry=None ):
				if button.get_active():
						assistant = self.builder.get_object( 'assistant_import_deutschepostcsv' )
						dialog = Gtk.FileChooserDialog( "Bitte Datei auswählen", self.builder.get_object( 'window' ), Gtk.FileChooserAction.OPEN, ( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK ) )
						filter_csv = Gtk.FileFilter()
						filter_csv.set_name( "CSV-Dateien" )
						filter_csv.add_pattern( "*.csv" )
						dialog.add_filter( filter_csv )
						response = dialog.run()
						if response == Gtk.ResponseType.OK:
								entry = self.builder.get_object( 'assistant_import_deutschepostcsv_open_entry' )
								entry.set_text( dialog.get_filename() )
								assistant.set_page_complete( assistant.get_nth_page( assistant.get_current_page() ), True )
						dialog.destroy()
						button.set_active( False )
						assistant.present()
