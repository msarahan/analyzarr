class MDAController(ControllerBase):
    # the image data for the factor plot (including any scatter data and
    #    quiver data)
    factor_plotdata = ArrayPlotData
    # the actual plot object
    factor_plot = t.Instance(BasePlotContainer)
    # the image data for the score plot (may be a parent image for scatter overlays)
    score_plotdata = ArrayPlotData
    score_plot = t.Instance(BasePlotContainer)

    def __init__(self, treasure_chest=None, data_path='/mda_results',
                 *args, **kw):
        super(ControllerBase, self).__init__(*args, **kw)
        self.factor_plotdata = ArrayPlotData()
        self.score_plotdata = ArrayPlotData()
        if treasure_chest is not None:
            self.chest = treasure_chest
            self.data_path = data_path
            # TODO: this is not a good way to do things.  MDA is split with
            #   two descriptors - the type of mda, then the date it was done.
            #   perhaps only do by date it was done?
            self.nodes = self.chest.listNodes(data_path)
            self.numfiles = self.chest.root.mda_description.nrows
            if self.numfiles > 0:
                self.init_plots()

    # TODO: need to rethink how to set_data for these things, since we have so
    #    many different places to put data.
    def init_plots(self):
        self.factor_plotdata.set_data('imagedata',
                                      self.get_active_factor_image())
        self.factor_plotdata.set_data('imagedata',
                                      self.get_active_score_image())
        self.factor_plot = self.render_factor_plot(
                img_data=self.factor_plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                )
        self.score_plot = self.render_score_plot(
                img_data=self.score_plotdata, scatter_data=self.score_plotdata,
                title="%s of %s: " % (self.selected_index + 1,
                                      self.numfiles) + self.get_active_name()
                )

    @t.on_trait_change("selected_index")
    def update_image(self):
        # TODO: customize this to change the factor data and plot data
        self.plotdata.set_data("imagedata", self.get_active_image())
        self.set_plot_title("%s of %s: " % (self.selected_index + 1,
                                          self.numfiles) + self.get_active_name())

    ######
    #  Analysis methods each create their own member under the group of MDA
    #  results in the chest.
    ######
    def PCA(self, n_components=None):
        self._create_new_context("PCA")

        active_data = self.get_active_image_set()
        data = active_data.reshape((active_data.shape[0], -1))
        factors, scores , eigenvalues = mda.PCA(data, n_components=n_components)
        factors, scores = self._reshape_MDA_results(active_data, factors, scores)
        fs = self.chest.createCArray(self.context, 'Factors',
                                     tb.Atom.from_dtype(factors.dtype),
                                     factors.shape,
                                     filters=filters
                                     )
        ss = self.chest.createCArray(self.context, 'Scores',
                                     tb.Atom.from_dtype(scores.dtype),
                                     scores.shape,
                                     filters=filters
                                     )
        ev = self.chest.createCArray(self.context, 'Eigenvalues',
                                     tb.Atom.from_dtype(eigenvalues.dtype),
                                     eigenvalues.shape,
                                     filters=filters
                                     )
        fs[:] = factors
        ss[:] = scores
        ev[:] = eigenvalues
        self.chest.flush()
        return factors, scores, eigenvalues
        # stash the results under the group of MDA results
        #   attribs:
        #   - analysis type
        #   - number of components
        #   - whitening applied
        # store the mean of each column - we use this for reconstruction later

    def ICA(self, n_components, whiten=False, max_iter=10):
        from scipy import integrate
        self._create_new_context("ICA")
        # reshape the data:
        #   The goal is always to have the variables (pixels in an image,
        #     energy channels in a spectrum) always as columns in a 2D array.
        #     The rows are made up of observations.  For example, in
        #     images, the rows are individual cells.  In SIs, the rows
        #     are pixels where spectra were gathered.
        # for images, the cell idx is dim 0
        data = self.data_controller.active_data_cube.reshape(
            (self.active_data.shape[0], -1))
        # for spectra, the energy index is dim 0.
        #data = spectrum_data.reshape((-1, data.shape[0]
        """
        Pre-processes the data to be ready for ICA.  Namely:
          differentiates the data (integrated ICA)
        """
        diffdata = data.copy()
        deriv_kernel = np.array([-1, 0, 0, 0, 0, 0, 1])
        for i in xrange(data.shape[1]):
            diffdata[:, i] = np.convolve(data[:, i], deriv_kernel)[3:-3]
        factors, scores = mda.ICA(diffdata, n_components=n_components)

        # integration undoes the differentiation done in the ICA data prep.
        factors = np.array([integrate.cumtrapz(factors[:, i])
                            for i in xrange(factors.shape[1])]).T
        factors, scores = self._reshape_MDA_results(
                            self.data_controller.active_data_cube,
                            factors, scores)
        fs = self.chest.createCArray(self.context, 'Factors',
                                     tb.Atom.from_dtype(factors.dtype),
                                     factors.shape,
                                     filters=filters
                                     )
        ss = self.chest.createCArray(self.context, 'Scores',
                                     tb.Atom.from_dtype(scores.dtype),
                                     scores.shape,
                                     filters=filters
                                     )
        fs[:] = factors
        ss[:] = scores
        self.chest.flush()
        return factors, scores

    def _reshape_MDA_results(self, data, factors, scores):
        # we need to reshape the factors and scores to make sense.
        # for images, the factors are themselves images, while the scores are
        # line plots with one column per component.
        if self.get_active_data_type() is "image":
            factors = factors.reshape((-1, data.shape[-2], data.shape[-1]))
            factors.squeeze()
            scores.reshape((data.shape[0], -1))
        # for SIs, the factors are spectra, while the scores are images.
        elif ((self.get_active_data_type() is "spectrum") or
                (self.get_active_data_type() is "peaks")):
            factors = factors.reshape((data.shape[0], -1))
            scores = scores.reshape((-1, data.shape[-2], data.shape[-1]))
            scores.squeeze()
        return factors, scores

    def _create_new_context(self, MDA_type):
        import time
        # first add an entry to our table of analyses performed
        datestr = MDA_type + time.strftime("_%Y-%m-%d %H:%M", time.localtime())
        data_record = self.chest.root.mda_description.row
        data_record['date'] = datestr
        data_record['mda_type'] = MDA_type
        data_record['input_data'] = self.data_controller.summarize_data()
        #data_record['treatments'] = self.data_controller.summarize
        data_record.append()
        # If this MDA type hasn't been done yet, add a member of the MDA group
        #   for this type.
        self.chest.createGroup
        # Set this instance's data as members of a group for the time right now
        # this is where the factors and scores result arrays will be stored.
        self.chest.flush()
        # context is a pytables group.  It has attributes for informational
        #   data, as well as being the container for any outputs.
        self.context = "/mda_results/%s/%s" % (MDA_type, datestr)