from wait_for import wait_for
from widgetastic.widget import (
    Checkbox,
    ConditionalSwitchableView,
    Select,
    Table,
    Text,
    TextInput,
    View,
)
from widgetastic_patternfly import BreadCrumb

from airgun.views.common import (
    BaseLoggedInView,
    SatTab,
    SearchableViewMixin,
    TaskDetailsView,
)
from airgun.views.syncplan import SyncPlanCreateView
from airgun.widgets import (
    ActionsDropdown,
    ConfirmationDialog,
    EditableEntry,
    EditableEntrySelect,
    ReadOnlyEntry,
    SatSelect,
    SatTable,
    Search,
)


class CreateDiscoveredReposView(View):
    """View which represent Discovered Repository section in Repository
    Discovery procedure.
    """

    searchbox = Search()
    table = SatTable(
        locator=".//table",
        column_widgets={0: Checkbox(locator=".//input[@ng-change='itemSelected(urlRow)']")},
    )
    create_action = Text("//button[contains(., 'Create Selected')]")

    def fill(self, values):
        """Select necessary repo/repos to be added to new or existing product"""
        if not isinstance(values, list):
            values = [values]
        for value in values:
            self.table.row(discovered_repository__contains=value)[0].fill(True)
            self.create_action.click()

    def read(self):
        return self.table.read()


class ProductsTableView(BaseLoggedInView, SearchableViewMixin):
    title = Text("//h2[contains(., 'Products')]")
    new = Text("//button[contains(@href, '/products/new')]")
    edit = Text(
        "//td/a[contains(@ui-sref, 'product.repositories') and contains(@href, 'products')]"
    )
    repo_discovery = Text("//button[contains(.,'Repo Discovery')]")
    actions = ActionsDropdown("//div[contains(@class, 'btn-group')]")
    table = Table(
        './/table',
        column_widgets={
            0: Checkbox(locator=".//input[@ng-change='itemSelected(product)']"),
            'Name': Text('./a'),
        },
    )
    dialog = ConfirmationDialog()

    @property
    def is_displayed(self):
        return self.browser.wait_for_element(self.title, exception=False) is not None


class ProductCreateView(BaseLoggedInView):
    breadcrumb = BreadCrumb()
    name = TextInput(id='name')
    label = TextInput(id='label')
    gpg_key = Select(id='gpg_key_id')
    ssl_ca_cert = Select(id='ssl_ca_cert_id')
    ssl_client_cert = Select(id='ssl_client_cert_id')
    ssl_client_key = Select(id='ssl_client_key_id')
    sync_plan = Select(id='sync_plan_id')
    create_sync_plan = Text("//a[contains(@ng-click, 'openSyncPlanModal')]")
    description = TextInput(id='description')
    submit = Text("//button[contains(@ng-click, 'handleSave')]")

    @property
    def is_displayed(self):
        breadcrumb_loaded = self.browser.wait_for_element(self.breadcrumb, exception=False)
        return (
            breadcrumb_loaded
            and self.breadcrumb.locations[0] == 'Products'
            and self.breadcrumb.read() == 'New Product'
        )


class ProductEditView(BaseLoggedInView):
    breadcrumb = BreadCrumb()
    BREADCRUMB_LENGTH = 3
    actions = ActionsDropdown("//div[contains(@class, 'btn-group')]")
    dialog = ConfirmationDialog()

    @property
    def is_displayed(self):
        breadcrumb_loaded = self.browser.wait_for_element(self.breadcrumb, exception=False)
        return (
            breadcrumb_loaded
            and self.breadcrumb.locations[0] == 'Products'
            and self.breadcrumb.read() not in ('New Product', 'Discover Repositories')
            and len(self.breadcrumb.locations) <= self.BREADCRUMB_LENGTH
        )

    @View.nested
    class details(SatTab):
        name = EditableEntry(name='Name')
        label = ReadOnlyEntry(name='Label')
        gpg_key = EditableEntrySelect(name='GPG Key')
        ssl_ca_cert = EditableEntrySelect(name='SSL CA Cert')
        ssl_client_cert = EditableEntrySelect(name='SSL Client Cert')
        ssl_client_key = EditableEntrySelect(name='SSL Client Key')
        description = EditableEntry(name='Description')
        repos_count = ReadOnlyEntry(name='Number of Repositories')
        tasks_count = ReadOnlyEntry(name='Active Tasks')
        sync_plan = EditableEntrySelect(name='Sync Plan')
        sync_state = ReadOnlyEntry(name='Sync State')

    @View.nested
    class repositories(SatTab):
        table = SatTable(
            locator=".//table",
            column_widgets={
                0: Checkbox(locator="./input[@ng-change='itemSelected(repository)']"),
                'Name': Text("./a"),
            },
        )


class ProductRepoDiscoveryView(BaseLoggedInView, SearchableViewMixin):
    breadcrumb = BreadCrumb()
    repo_type = Select(locator="//select[@ng-model='discovery.contentType']")
    url = TextInput(id='urlToDiscover')
    registry_type = Select(id='registry_type')
    username = TextInput(id='upstreamUsername')
    password = TextInput(id='upstreamPassword')
    registry_search = TextInput(id='registrySearch')

    @property
    def is_displayed(self):
        breadcrumb_loaded = self.browser.wait_for_element(self.breadcrumb, exception=False)
        return (
            breadcrumb_loaded
            and self.breadcrumb.locations[0] == 'Products'
            and self.breadcrumb.read() == 'Discover Repositories'
        )

    @View.nested
    class discovered_repos(View):
        discover_action = Text("//button[@type='submit' and contains(., 'Discover')]")
        cancel_discovery = Text("//button[@ng-click='cancelDiscovery()']")
        repos = CreateDiscoveredReposView()

        def before_fill(self, values=None):
            """After we filled 'repository type' and 'url' fields, we need to
            push 'Discover' button to get table populated with values. Using
            before_fill to not define any method explicitly which need to be
            called and break view.fill() procedure flow
            """
            self.discover_action.click()
            wait_for(
                lambda: self.cancel_discovery.is_displayed is False,
                timeout=300,
                delay=1,
                logger=self.logger,
            )

    @View.nested
    class create_repo(View):
        """Represent Create Repository page. Depends whether we like create new
        product or use existing one we use different sets of fields that need
        to be filled
        """

        product_type = SatSelect(locator="//select[@ng-model='createRepoChoices.newProduct']")
        product_content = ConditionalSwitchableView(reference='product_type')

        @product_content.register('Existing Product')
        class ExistingProductForm(View):
            product_name = Select(
                locator="//select[@ng-model='createRepoChoices.existingProductId']"
            )

        @product_content.register('New Product')
        class NewProductForm(View):
            product_name = TextInput(id='productName')
            label = TextInput(id='productLabel')
            gpg_key = Select(locator="//select[contains(@ng-model,'gpg_key_id')]")

        serve_via_http = Checkbox(id='unprotected')
        verify_ssl = Checkbox(id='verify_ssl')
        run_procedure = Text("//button[contains(., 'Run Repository Creation')]")
        create_repos_table = Table(
            locator='//table',
            column_widgets={
                'Repository Name': TextInput(locator=".//input[@name='repo_name']"),
                'Repository Label': TextInput(locator=".//input[@name='repo_label']"),
            },
        )

        def wait_repo_created(self):
            wait_for(
                lambda: self.create_repos_table.row(
                    create_status__contains='Repository created'
                ).is_displayed
                is True,
                timeout=300,
                delay=1,
                logger=self.logger,
            )


class ProductTaskDetailsView(TaskDetailsView):
    BREADCRUMB_LENGTH = 3

    @property
    def is_displayed(self):
        breadcrumb_loaded = self.browser.wait_for_element(self.breadcrumb, exception=False)
        return (
            breadcrumb_loaded
            and self.breadcrumb.locations[0] == 'Products'
            and self.breadcrumb.locations[2] == 'Tasks'
            and len(self.breadcrumb.locations) > self.BREADCRUMB_LENGTH
        )


class ProductSyncPlanView(SyncPlanCreateView):
    title = Text("//h4[contains(., 'New Sync Plan')]")
    submit = Text("//button[contains(@ng-click, 'ok(syncPlan)')]")

    @property
    def is_displayed(self):
        return self.browser.wait_for_element(self.title, exception=False) is not None


class ProductManageHttpProxy(BaseLoggedInView):
    """Represents Http proxy Management page for Products."""

    title = Text("//h4[normalize-space(.)='HTTP proxy Management']")
    http_proxy_policy = Select(id="http_proxy_policy")
    proxy_policy = ConditionalSwitchableView(reference='http_proxy_policy')
    update = Text('//button[@ng-click="update()"]')

    @proxy_policy.register('Use specific HTTP proxy')
    class ExistingProductForm(View):
        http_proxy = Select(id="http_proxy")

    @property
    def is_displayed(self):
        return self.browser.wait_for_element(self.title, exception=False) is not None


class ProductAdvancedSync(BaseLoggedInView):
    """Represents Advanced Sync page for Products."""

    title = Text("//h4[normalize-space(.)='Advanced Sync']")
    optimized = Text("//input[contains(@value, 'standard')]")
    complete = Text("//input[contains(@value, 'skipMetadataCheck')]")
    task = Text("//a[normalize-space(.)='Click to view task']")
    sync = Text('//button[@ng-click="ok()"]')

    @property
    def is_displayed(self):
        return self.browser.wait_for_element(self.title, exception=False) is not None


class ProductVerifyContentChecksum(BaseLoggedInView):
    """Represents Verify Content Checksum Alert page for Products."""

    task_alert = Text("//a[normalize-space(.)='Click to monitor task progress.']")

    @property
    def is_displayed(self):
        return self.browser.wait_for_element(self.task_alert, exception=False) is not None
