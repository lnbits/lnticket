const mapLNTicket = function (obj) {
  obj.date = Quasar.date.formatDate(
    new Date(obj.time * 1000),
    'YYYY-MM-DD HH:mm'
  )
  obj.fsat = new Intl.NumberFormat(LOCALE).format(obj.amount)
  obj.displayUrl = ['/lnticket/', obj.id].join('')
  return obj
}

window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data: function () {
    return {
      forms: [],
      tickets: [],
      formsTable: {
        columns: [
          {name: 'id', align: 'left', label: 'ID', field: 'id'},
          {name: 'name', align: 'left', label: 'Name', field: 'name'},
          {name: 'wallet', align: 'left', label: 'Wallet', field: 'wallet'},
          {
            name: 'webhook',
            align: 'left',
            label: 'Webhook',
            field: 'webhook'
          },
          {
            name: 'description',
            align: 'left',
            label: 'Description',
            field: 'description'
          },
          {
            name: 'flatrate',
            align: 'left',
            label: 'Flat Rate',
            field: 'flatrate'
          },
          {
            name: 'amount',
            align: 'left',
            label: 'Amount',
            field: 'amount'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      ticketsTable: {
        columns: [
          {name: 'form', align: 'left', label: 'Form', field: 'form'},
          {name: 'name', align: 'left', label: 'Name', field: 'name'},
          {name: 'email', align: 'left', label: 'Email', field: 'email'},
          {name: 'ltext', align: 'left', label: 'Ticket', field: 'ltext'},
          {name: 'sats', align: 'left', label: 'Cost', field: 'sats'}
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      formDialog: {
        show: false,
        data: {flatrate: false}
      },
      ticketDialog: {
        show: false,
        data: {}
      }
    }
  },
  computed: {
    flatRate: function () {
      if (this.formDialog.data.flatrate) {
        return 'Charge flat rate'
      } else {
        return 'Charge per word'
      }
    }
  },
  methods: {
    resetForm() {
      this.formDialog.data = {flatrate: false}
    },
    getTickets() {
      LNbits.api
        .request(
          'GET',
          '/lnticket/api/v1/tickets?all_wallets=true',
          this.g.user.wallets[0].adminkey
        )
        .then(response => {
          this.tickets = response.data
            .map(function (obj) {
              if (!obj?.paid) return
              return mapLNTicket(obj)
            })
            .filter(v => v)
        })
    },
    deleteTicket(ticketId) {
      const tickets = _.findWhere(this.tickets, {id: ticketId})

      LNbits.utils
        .confirmDialog('Are you sure you want to delete this ticket')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/lnticket/api/v1/tickets/' + ticketId,
              _.findWhere(this.g.user.wallets, {id: tickets.wallet}).adminkey
            )
            .then(response => {
              this.tickets = _.reject(this.tickets, obj => {
                return obj.id == ticketId
              })
            })
            .catch(LNbits.utils.notifyApiError)
        })
    },
    ticketCard(ticket) {
      this.ticketDialog.show = true
      let {date, email, ltext, name} = ticket.row
      this.ticketDialog.data = {
        date,
        email,
        content: ltext,
        name
      }
    },
    exportticketsCSV() {
      LNbits.utils.exportCSV(this.ticketsTable.columns, this.tickets)
    },

    getForms() {
      LNbits.api
        .request(
          'GET',
          '/lnticket/api/v1/forms?all_wallets=true',
          this.g.user.wallets[0].adminkey
        )
        .then(response => {
          this.forms = response.data.map(obj => {
            return mapLNTicket(obj)
          })
        })
    },
    sendFormData() {
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })
      this.formDialog.data.inkey = wallet.inkey
      const data = this.formDialog.data

      if (data.id) {
        this.updateForm(wallet, data)
      } else {
        this.createForm(wallet, data)
      }
    },

    createForm(wallet, data) {
      LNbits.api
        .request('POST', '/lnticket/api/v1/forms', wallet.adminkey, data)
        .then(response => {
          this.forms.push(mapLNTicket(response.data))
          this.formDialog.show = false
          this.resetForm()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    updateformDialog(formId) {
      const link = _.findWhere(this.forms, {id: formId})
      this.formDialog.data.id = link.id
      this.formDialog.data.wallet = link.wallet
      this.formDialog.data.name = link.name
      this.formDialog.data.description = link.description
      this.formDialog.data.flatrate = Boolean(link.flatrate)
      this.formDialog.data.amount = link.amount
      this.formDialog.show = true
    },
    updateForm(wallet, data) {
      LNbits.api
        .request(
          'PUT',
          '/lnticket/api/v1/forms/' + data.id,
          wallet.adminkey,
          data
        )
        .then(response => {
          this.forms = _.reject(this.forms, function (obj) {
            return obj.id == data.id
          })
          this.forms.push(mapLNTicket(response.data))
          this.formDialog.show = false
          this.resetForm()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    deleteForm(formsId) {
      const forms = _.findWhere(this.forms, {id: formsId})

      LNbits.utils
        .confirmDialog('Are you sure you want to delete this form link?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/lnticket/api/v1/forms/' + formsId,
              _.findWhere(this.g.user.wallets, {id: forms.wallet}).adminkey
            )
            .then(() => {
              this.forms = _.reject(this.forms, function (obj) {
                return obj.id == formsId
              })
            })
            .catch(LNbits.utils.notifyApiError)
        })
    },
    exportformsCSV() {
      LNbits.utils.exportCSV(this.formsTable.columns, this.forms)
    }
  },
  created() {
    if (this.g.user.wallets.length) {
      this.getTickets()
      this.getForms()
    }
  }
})
