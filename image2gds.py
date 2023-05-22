import pya

class MenuAction(pya.Action):
    def __init__(self, title, shortcut, action):
        self.title = title
        self.shortcut = shortcut
        self.action = action
    
    def triggered(self):
        self.action(self)

class Image2GDSHandler:
    def __call__(self, action):
        # Defines the GDS2 layers where the three channels go.
        gds2_layers = [
            pya.LayerInfo(1, 0),  # Red channel (layer, datatype)
            pya.LayerInfo(2, 0),  # Green channel (layer, datatype)
            pya.LayerInfo(3, 0),  # Blue channel (layer, datatype)
        ]

        app = pya.Application.instance()
        mw = app.main_window()

        lv = mw.current_view()
        if lv is None:
            raise Exception("No view selected")

        cv = lv.active_cellview()
        if not cv.is_valid():
            raise Exception("No cell or no layout found")

        # Create the layers if they do not exist already.
        # Prepare a vector (layers) which contains the layer indices for the relevant layers.
        layers = []

        for l in gds2_layers:
            layer = -1

            for li in cv.layout().layer_indices():
                if cv.layout().get_info(li).is_equivalent(l):
                    layer = li
                    break

            if layer < 0:
                # Layer does not exist yet: create a new layer (both in the layout and the layer list)
                layer = cv.layout().insert_layer(l)

                lp = pya.LayerPropertiesNode()
                lp.source_layer = l.layer
                lp.source_datatype = l.datatype
                lv.init_layer_properties(lp)
                lv.insert_layer(lv.end_layers(), lp)

            layers.append(layer)

        # This call is important to keep the layer list consistent when layers have been added or removed
        lv.update_content()

        # Prepare an array of all images in the view
        images = []
        lv.each_image(lambda i: images.append(i))

        # The database unit
        dbu = cv.layout().dbu

        if images:
            # Start transaction for "undo"
            lv.transaction("Image channels to RGB")

            # Iterate over all images
            for image in images:
                # This transformation will transform a pixel to the target location of the pixel in the layout
                trans = pya.ICplxTrans.from_dtrans(pya.DCplxTrans(1 / dbu) * image.trans() * pya.DCplxTrans(dbu))

                # The dimension of one pixel
                pw = image.pixel_width / dbu
                ph = image.pixel_height / dbu

                # Iterate over all channels
                for c in range(len(layers)):
                    # That is where the shapes go
                    shapes = cv.cell().shapes(layers[c])

                    # Iterate over all rows
                    for y in range(image.height):
                        # Iterate over all columns
                        for x in range(image.width):
                            # Use each channel for a different layer
                            # d > 0.5 selects all pixels with a level >50% in that channel
                            d = image.get_pixel(x, y, c)
                            if d > 0.5:
                                # Create a polygon corresponding to one pixel
                                p1 = pya.DPoint(x * pw, y * ph)
                                p2 = pya.DPoint((x + 1) * pw, (y + 1) * ph)
                                dbox = pya.DBox(p1, p2)
                                box = pya.Box.from_dbox(dbox)
                                poly = pya.Polygon(box)
                                shapes.insert(poly.transformed_cplx(trans))

            # Commit transaction
            lv.commit()


image2gds_handler = MenuAction("Image channels to layers", "", Image2GDSHandler())

app = pya.Application.instance()
mw = app.main_window()

menu = mw.menu()
menu.insert_separator("tools_menu.end", "name")
menu.insert_item("tools_menu.end", "image2gds", image2gds_handler)
